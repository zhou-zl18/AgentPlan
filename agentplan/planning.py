"""Community division, planning, checkpoint initialization, and resume."""
import copy
import json
import os
import pickle
import random
import time
import json_repair
from tqdm import tqdm
from . import llm
from .agents import Planner, Resident
from .config import PLANNER_MODEL, RESIDENTS_MODEL, MAX_ROUND, data_path, evaluation_config
from .constraints import evaluate_requirements
from .data import load_experiment_data
from .environment import Environment
from .feedback import get_plan_description, evaluate_plan
from .landuse import cates_str2list
from .constraints import get_feasible_cates
from .llm import get_multiple_completion
from .spatial import get_distance_to_community
from .prompts import (
    basemap_description, planner_system_prompt, planner_community_division_prompt,
    planner_community_first_prompt, planner_action_prompt, ask_resident_prompt,
    planner_update_memory_prompt, conflict_resident_prompt,
)


def solve_conflict(requirement_violate, resident_suggestions, environment, round_record, residents):
    auto_correction_log = 'There are some areas that do not meet the planning requirements. We have automatically modified the POI types through voting based on residents\' suggestions.\n'
    for x in requirement_violate:
        error_info = f"Area {x['id']}, {int(x['area'])} m^2, POIs: {x['POI_cates']}, {','.join(x['errors'])}\n"
        auto_correction_log += error_info
        # Calculate scores for each facility type based on resident suggestions
        POI_cates = cates_str2list(x['POI_cates'])
        

        # find all residents that have suggestions for this area
        conflict_residents_ids = []
        for rid, suggestion in resident_suggestions.items(): # resident_suggestions[resident.id] = suggestions
            '''
            {{
            "Area <id>": {{
                "POI type": score,
                ...
            }},
            ...
            '''
            if f"Area {x['id']}" in suggestion:
                area_suggestion = suggestion[f"Area {x['id']}"]
                if len(area_suggestion) > 0: 
                    conflict_residents_ids.append(rid)

        # calculate facility scores
        facility_scores = {x:0 for x in POI_cates}
        for i in conflict_residents_ids:
            area_suggestion = resident_suggestions[i][f"Area {x['id']}"]
            for facility, score in area_suggestion.items():
                if facility in facility_scores.keys():
                    facility_scores[facility] += score
        
        area_correction_record = {
            'error_info': x,
            'conflict_residents_ids': conflict_residents_ids,
            'old_resident_suggestions': copy.deepcopy(resident_suggestions),
            'old_facility_scores': facility_scores,
        }

        print(f'Conflict residents for Area {x["id"]}:', conflict_residents_ids)
        print('Discuss to update suggestions...')
        prompts = []
        # conflict residents update suggestions
        for i in conflict_residents_ids:
            resident = residents[i]
            neighborhood_description = resident.get_areas_description(environment.gdf, resident.area_15min + resident.fix_area_15min)
            area_suggestions = resident_suggestions[i][f"Area {x['id']}"]
            others_area_suggestions = ''
            for j in conflict_residents_ids:
                if j == i:
                    continue
                others_area_suggestions += residents[j].profile
                others_area_suggestions += f'Suggestions: ' + str(resident_suggestions[j][f"Area {x['id']}"]) + '\n'
            prompt = conflict_resident_prompt.format(neighborhood_description=neighborhood_description, 
                                                     error_info=error_info, 
                                                     area_suggestions=area_suggestions, 
                                                     others_area_suggestions=others_area_suggestions)
            prompts.append(prompt)
            resident.append_message(prompt=prompt)
        
        tmp = [residents[i].messages for i in conflict_residents_ids]
        responses = get_multiple_completion(tmp, model=RESIDENTS_MODEL, use_tqdm=True) # response: {"Reason": "", "Suggestions": {}}
        for i, response in zip(conflict_residents_ids, responses):
            residents[i].append_message(response=response)

            # update resident_suggestions
            res_json = json_repair.loads(response)
            new_suggestions = res_json.get('Suggestions', {})
            for area_key, area_suggestion in new_suggestions.items():
                resident_suggestions[i][area_key] = area_suggestion


        # calculate facility scores
        facility_scores = {x:0 for x in POI_cates}
        for i in conflict_residents_ids:
            area_suggestion = resident_suggestions[i][f"Area {x['id']}"]
            for facility, score in area_suggestion.items():
                if facility in facility_scores.keys():
                    facility_scores[facility] += score

        # add facilities based on scores and feasibility
        sorted_facilities = sorted(facility_scores.items(), key=lambda item: item[1], reverse=True)
        new_facilities = []
        for facility in sorted_facilities:
            facility_type, score = facility
            feasible_cates = get_feasible_cates(new_facilities, x['area'])
            if facility_type in feasible_cates:
                new_facilities.append(facility_type)
        # environment.update_gdf_by_json({f"Area {x['id']}": new_facilities})
        environment.update_area(x['id'], new_facilities)
        auto_correction_log += f'Based on residents\' suggestions, the modified POI types in Area {x["id"]} are: {",".join(new_facilities)}\n'

        area_correction_record['prompts'] = prompts
        area_correction_record['responses'] = responses
        area_correction_record['new_facility_scores'] = facility_scores
        area_correction_record['new_facilities'] = new_facilities
        
        round_record['auto_corrections'].append(area_correction_record)
        
    return auto_correction_log

def initialize_experiment(dataset, exppath):
    filepath = data_path(dataset)
    evaluation_configs = evaluation_config(dataset)
    distance_15min = evaluation_configs['distance_15min']
    gdf, agentdf, agent_area_dist, agent_area_direction = load_experiment_data(filepath)
    environment = Environment(init_gdf=gdf, agentdf=agentdf)
    # init residents
    residents = []
    for index, row in tqdm(agentdf.iterrows()):
        info = row.to_dict()
        resident = Resident(info=info, gdf=gdf, agent_area_dist=agent_area_dist, agent_area_direction=agent_area_direction, distance_15min=distance_15min)
        residents.append(resident)
    print(len(residents))

    # init planner
    basemap_image_path = os.path.join(filepath,'basemap_proj.jpg')
    assert os.path.exists(basemap_image_path)

    plan_description = get_plan_description(gdf)
    system_prompt = planner_system_prompt.format(basemap_description=basemap_description, plan_description=plan_description)
    planner = Planner(system_prompt=system_prompt, image_path=basemap_image_path, model=PLANNER_MODEL)

    llm.LLM_USAGE = {
        'gpt-3.5-turbo': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0},
        'gpt-4o-mini': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0},
        'gpt-4o': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0},
    }

    prompt = planner_community_division_prompt
    print(prompt)

    response = planner.chat(prompt, with_history=False)
    print(response)

    community2areas = json_repair.loads(response)
    if isinstance(community2areas, list): # handling possible errors
        community2areas = community2areas[1]
    if not isinstance(community2areas, dict):
        raise ValueError(f"Invalid response format: {response}")
    print('#Community =', len(community2areas))
    print(community2areas)

    # 是否包含了所有non-residential areas
    areas = []
    for k,v in community2areas.items():
        areas.extend(v)
    print(len(set(areas)))
    changeable_areas = gdf[gdf['type'].isin(['vacant','changeable'])]['id'].tolist()
    fixed_areas = gdf[gdf['type'].isin(['fixed'])]['id'].tolist()
    print('The following areas are not included in any community:')
    print('changeable:', [x for x in changeable_areas if x not in areas])
    print('fixed:', [x for x in fixed_areas if x not in areas])
    # 未包括进去的，合并到最近的community
    no_included_areas = [x for x in changeable_areas if x not in areas] + [x for x in fixed_areas if x not in areas]

    for area_id in no_included_areas:
        community_distance = []
        for community_id, community_area_ids in community2areas.items():
            distance = get_distance_to_community(gdf, area_id, community_area_ids)
            community_distance.append((community_id, distance))
        community_distance.sort(key=lambda x: x[1])
        nearest_community = community_distance[0][0]
        community2areas[nearest_community].append(area_id)
        print(f'Area {area_id}->Community {nearest_community}')
    environment.community2areas = community2areas

    output = copy.deepcopy(community2areas)
    output['reasoning'] = response
    assert not os.path.exists(os.path.join(exppath, "community2areas.geojson"))
    with open(os.path.join(exppath, "community2areas.geojson"),'w') as f:
        json.dump(community2areas, f)

    records = {
        "Community_Division": {"usage": llm.LLM_USAGE, "prompt": prompt, "response": response}
        }
    with open(os.path.join(exppath, "records_community0.json"), 'w') as f:
        json.dump(records, f, indent=4)
    with open(os.path.join(exppath, "planner_community0.pkl"), 'wb') as file:
        pickle.dump(planner, file)
    with open(os.path.join(exppath, "residents_community0.pkl"), 'wb') as file:
        pickle.dump(residents, file)
    with open(os.path.join(exppath, "environment_community0.pkl"), 'wb') as file:
        pickle.dump(environment, file)
    return planner, residents, environment, records, agentdf, agent_area_dist, evaluation_configs


def resume_experiment(dataset, exppath, cid):
    with open(os.path.join(exppath, f"records_community{cid}.json"), 'r') as f:
        records = json.load(f)
    with open(os.path.join(exppath, f"planner_community{cid}.pkl"), 'rb') as file:
        planner = pickle.load(file)
    with open(os.path.join(exppath, f"residents_community{cid}.pkl"), 'rb') as file:
        residents = pickle.load(file)
    with open(os.path.join(exppath, f"environment_community{cid}.pkl"), 'rb') as file:
        environment = pickle.load(file)
    llm.LLM_USAGE = list(records.values())[-1]['usage']
    # Rebuild geometric distances and resolve the local map path.
    _, _, agent_area_dist, _ = load_experiment_data(data_path(dataset))
    agentdf = environment.agentdf
    planner.image_path = data_path(dataset) / 'basemap_proj.jpg'
    return planner, residents, environment, records, agentdf, agent_area_dist, evaluation_config(dataset)


def run_planning(planner, residents, environment, records, agentdf,
                 agent_area_dist, evaluation_configs, exppath):
    print(llm.LLM_USAGE)
    for k, areas in environment.community2areas.items():
        community_id = str(k)
        if community_id in environment.finished_communities:
            print(f'Community {community_id} already finished, skip.')
            continue

        print(f'-------------------Community {community_id} Start!-------------------')
        start_time = time.time()

        changeable_areas = []
        fixed_areas = []
        for area_id in areas:
            area_type = environment.gdf.loc[environment.gdf['id'] == area_id, 'type'].iloc[0]
            if area_type in ['vacant', 'changeable']:
                changeable_areas.append(area_id)
            else:
                fixed_areas.append(area_id)
        print(f'Total areas: {len(areas)}')
        print(f'Changeable areas: {len(changeable_areas)}')
        print(f'Fixed areas: {len(fixed_areas)}')

        # initial schedule for this community
        prompt = planner_community_first_prompt.format(community_id=community_id, changeable_areas=changeable_areas, fixed_areas=fixed_areas)
        response = planner.chat(prompt)
        time.sleep(1)
        res_json = json_repair.loads(response)
        plan = res_json['plan']
        planner.update_plan(plan)
        print(f'Plan:\n{plan}')

        community_records = {"Round 0": {"prompt": prompt, "response": response}}

        resident_suggestions = {}
        planner_round = 0

        while True:
            planner_round += 1
            print(f'------------------Round {planner_round}------------------')
            if planner_round > MAX_ROUND:
                print('===============================')
                print('Max round reached!!')
                print('===============================')
                break
        
            # action
            prompt = planner_action_prompt
            response = planner.chat(prompt)
            time.sleep(1)

            res_json = json_repair.loads(response)
            action = res_json['Action']
            input = res_json['Input']

            print('Action:', action)

            round_record = {
                "action_prompt": prompt,
                "action_response": response,
                "action": action,
                "input": input,
            }

            if action == 'VIEW_RESIDENTS':
                print('View areas:', input)
                if isinstance(input, str):  # in case input = "[1,2,3]"
                    input = eval(input)
                nearby_residents_ids = []
                for i, resident in enumerate(residents):
                    if len(set(resident.area_15min).intersection(set(input))) > 0:
                        nearby_residents_ids.append(i)
                output = ''
                for i in nearby_residents_ids:
                    output += residents[i].profile +'\n'

                print(f'Viewed {len(nearby_residents_ids)} residents.')

            elif action == 'LAUNCH_DISCUSSION':
                print('Discussion rounds:', len(input))
                print(input)
                if not isinstance(input, list):
                    output = """Invalid input. You should input a list of resident ids (integers). If you don't know resident ids, try other actions first."""
                    print(output)
                    continue

                discussion_summary = ''
                full_discussion_history = ''
                round_record['discussion_records'] = []
                selected_residents_idxs = list(set(input))


                prompts = []
                if len(selected_residents_idxs) > 50:
                    selected_residents_idxs = random.sample(selected_residents_idxs, 50)
                for i in selected_residents_idxs:
                    resident = residents[i]
                    neighborhood_description = resident.get_areas_description(environment.gdf, resident.area_15min + resident.fix_area_15min)
                    prompt = ask_resident_prompt.format(neighborhood_description=neighborhood_description, community_id=community_id, changeable_areas=changeable_areas)

                    prompts.append(prompt)
                    resident.append_message(prompt=prompt)

                tmp = [residents[i].messages for i in selected_residents_idxs]
                responses = get_multiple_completion(tmp, model=RESIDENTS_MODEL, use_tqdm=True) # response: {"Reason": "", "Suggestions": {}}
                for i, response in zip(selected_residents_idxs, responses):
                    residents[i].append_message(response=response)
            
                round_record['discussion_records'].append({
                    'resident_ids': selected_residents_idxs,
                    'prompts': prompts,
                    'responses': responses,
                })

                # agent opinions str
                agent_opinions = ''
                for i in selected_residents_idxs:
                    resident = residents[i]
                    tmp = resident.profile
                    tmp += f"Nearby Area ids (within 15-minute life circle): {resident.area_15min}\n"
                    tmp = tmp + 'Opinion:\n' + resident.messages[-1]['content'] + '\n'
                    agent_opinions += tmp

                    res_json = json_repair.loads(resident.messages[-1]['content'])
                    suggestions = res_json['Suggestions']
                    if len(suggestions) > 0:
                        resident_suggestions[resident.id] = suggestions

                full_discussion_history += agent_opinions


                output = ''
                output += f'Summary of discussion:\n{full_discussion_history}\n'
                
            elif action == 'UPDATE_PLAN':
                plan_json = input
                gdf = environment.update_gdf_by_json(plan_json)
                # record
                environment.add_update_record(plan_json)

                # 如果有不满足要求(超出或冲突)，将现有设施按居民投票进行排序，从高到低依次保留
                gdf = environment.gdf.copy()
                requirement_violate = evaluate_requirements(gdf, areas)
                round_record['auto_corrections'] = []
                if len(requirement_violate) > 0:
                    auto_correction_log = solve_conflict(requirement_violate, resident_suggestions, environment, round_record, residents)
                else:
                    auto_correction_log = ''
                
                gdf = environment.gdf.copy()
                output = auto_correction_log
                output += evaluate_plan(gdf, agentdf, agent_area_dist, evaluation_configs, focus_areas=areas)
                print('Feedback:\n', output)
            

            elif action == 'EVALUATE_PLAN':
                gdf = environment.gdf.copy()
                output = evaluate_plan(gdf, agentdf, agent_area_dist, evaluation_configs, focus_areas=areas)
                print('Feedback:\n', output)


            elif action == 'FINISH_PLANNING':
                output = f'You finish planning for Community {community_id}.'
                break

            else:
                output = 'Invalid action. Please input again.'

            planner.update_action_history(action, input, output)
        

            # update memory
            print('## update memory and plan ##')
            prompt = planner_update_memory_prompt.format(output=output)
            response = planner.chat(prompt)
            time.sleep(1)
            res_json = json_repair.loads(response)
            new_memory = res_json['memory'] if 'memory' in res_json else res_json['Memory']
            new_plan = res_json['plan'] if 'plan' in res_json else res_json['Plan']
            new_memory = str(new_memory)
            new_plan = str(new_plan)
            planner.update_memory(new_memory)
            planner.update_plan(new_plan)
            print(f'Memory:\n{new_memory}')
            print(f'Plan:\n{new_plan}')

            round_record['feedback'] = output
            round_record['update_memory_plan_prompt'] = prompt
            round_record['update_memory_plan_response'] = response
            round_record['new_memory'] = new_memory
            round_record['new_plan'] = new_plan
            community_records[f'Round {planner_round}'] = round_record

            print('time:', time.time()-start_time)

    
        print(llm.LLM_USAGE)
        environment.finished_communities.append(community_id)
        community_records['usage'] = llm.LLM_USAGE
        records[f'Community_{community_id}'] = community_records
        with open(os.path.join(exppath, f"records_community{community_id}.json"), 'w') as f:
            json.dump(records, f, indent=4)
        with open(os.path.join(exppath, f"planner_community{community_id}.pkl"), 'wb') as file:
            pickle.dump(planner, file)
        with open(os.path.join(exppath, f"residents_community{community_id}.pkl"), 'wb') as file:
            pickle.dump(residents, file)
        with open(os.path.join(exppath, f"environment_community{community_id}.pkl"), 'wb') as file:
            pickle.dump(environment, file)
        print(f'-------------------Community {community_id} Finished!-------------------')
        # break


def save_results(planner, residents, environment, records, exppath):
    # save plan
    filename = os.path.join(exppath,"plan.geojson")
    print(filename)
    assert not os.path.exists(filename)
    environment.gdf.to_file(filename, driver='GeoJSON')
    # save log
    filename = os.path.join(exppath,'planner_messages.json')
    with open(filename, 'w') as f:
        json.dump(planner.chat_history, f)
    
    with open(os.path.join(exppath, "records.json"), 'w') as f:
        json.dump(records, f, indent=4)
    with open(os.path.join(exppath, "planner.pkl"), 'wb') as file:
        pickle.dump(planner, file)
    with open(os.path.join(exppath, "residents.pkl"), 'wb') as file:
        pickle.dump(residents, file)
    with open(os.path.join(exppath, "environment.pkl"), 'wb') as file:
        pickle.dump(environment, file)
