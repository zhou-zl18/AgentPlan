"""Textual plan descriptions and feedback supplied to the planner."""
from .constraints import evaluate_requirements, check_feasible_areas
from .metrics import evaluate

def get_plan_description(gdf, focus_areas=None):
    if focus_areas is None:
        focus_areas = gdf['id'].tolist()

    focus_gdf = gdf[gdf['id'].isin(focus_areas)]
    changeable_area_ids = focus_gdf[focus_gdf['type'].isin(['changeable','vacant'])]['id'].tolist()
    fixed_area_ids = focus_gdf[focus_gdf['type'] == 'fixed']['id'].tolist()
    plan_description = f'There are {len(changeable_area_ids)} changeable areas that you can modify the POI types: {changeable_area_ids}.\n'
    plan_description += f'There are {len(fixed_area_ids)} fixed areas that you cannot modify the POI types: {fixed_area_ids}.\n'
    plan_description += 'The sizes of all areas are fixed and you cannot modify them.\n'

    plan_description += 'The POI categories in each area are as follows:\n'
    # changeable and vacant areas
    for id, row in focus_gdf.iterrows():
        area_id = row['id']
        tp = row['type']

        if tp in ['changeable','vacant']:
            POI_cates = row['POI_cates']
            area_size = int(row['area'])
            plan_description += f'Area {area_id} ({area_size} m^2): {POI_cates}.\n'
        
    plan_description += 'The above areas are changeable and you can modify the POI types. The following areas are fixed and you cannot modify the POI there.\n'
    # fixed areas
    for id, row in focus_gdf.iterrows():
        area_id = row['id']
        tp = row['type']
        if tp in ['fixed']:
            POI_cates = row['POI_cates']
            area_size = int(row['area'])
            plan_description += f'Area {area_id} ({area_size} m^2): {POI_cates}.\n'
    return plan_description

def evaluate_plan(gdf, agentdf, agent_area_dist, evaluation_configs, focus_areas=None) -> str: # return a textual evaluation
    if focus_areas is None:
        focus_areas = gdf['id'].tolist()

    gdf['POI_cates'] = gdf['POI_cates'].fillna('')
    plan_description = get_plan_description(gdf, focus_areas=focus_areas)
    prompt = f'The current plan is described as follows:\n{plan_description}\n'

    requirement_violate = evaluate_requirements(gdf, focus_areas)
    if len(requirement_violate) > 0:
        prompt = 'The following areas does not meet the requirement:\n'
        for x in requirement_violate:
            prompt += f"Area {x['id']}, {int(x['area'])} m^2, POIs: {x['POI_cates']}, {','.join(x['errors'])}\n"
        prompt += 'Please revise the plan. You should choose the UPDATE_PLAN action and tell me your new plan.'
        return prompt
        
    # calculate metrics
    walk_score, service_agent, sat, spe_sat, walk_equality, service_equality, satisfaction_equality = evaluate(gdf, agentdf, agent_area_dist, evaluation_configs)
    
    prompt = f'The requirements are satisfied. Evaluation metrics of your plan are as follows:'
    prompt += f"Walk score={walk_score:.3f}, Residents satisfaction={sat:.3f}\n"
    
    # check if any available space
    feasible_areas = check_feasible_areas(gdf, focus_areas=focus_areas)
    if len(feasible_areas) > 0:
        prompt += 'There are some extra space available in some areas:\n'
        for x in feasible_areas: # [area_id, cur_cates, feasible_cates]
            area_id, cur_cates, feasible_cates = x
            prompt += f"Area {area_id}: \nCurrent POI types: {str(cur_cates)}\nFeasible POI types: {str(feasible_cates)}\n"
        prompt += "Note that you may not add all the feasible POIs into an area. You should consider the area size limit."
    return prompt
