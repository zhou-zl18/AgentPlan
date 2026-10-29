"""Evaluation metrics shared by experiment and evaluation entry points."""
import numpy as np
import pandas as pd
from tqdm import tqdm
from shapely.geometry import Point
from .landuse import cates_str2list

METRIC_NAMES = (
    'Walk score',
    'Service',
    'Satisfaction',
    'Inclusion',
    'Walk score equality',
    'Service equality',
    'Satisfaction equality',
)

def gini_coefficient(x):
    """Compute Gini coefficient of array of values"""
    x=np.array(x)
    diffsum = 0
    for i, xi in enumerate(x[:-1], 1):
        diffsum += np.sum(np.abs(xi - x[i:]))
    return diffsum / (len(x)**2 * np.mean(x))


def calculate_walk_score(gdf, agentdf, agent_area_dist, evaluation_configs):
    walkscore_min_dist = evaluation_configs['walkscore_min_dist']
    walkscore_max_dist = evaluation_configs['walkscore_max_dist']

    all_cates = ['life service', 'office', 'park', 'education','medical', 'recreation', 'restaurant', 'shopping']

    gdf_copy = gdf.copy()
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].fillna('')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('educational facility', 'education')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('school', 'education')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('medical facility', 'medical')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('hospital', 'medical')

    cate2areas = {cate:[] for cate in all_cates}
    for area_id, POI_cates_str in zip(gdf_copy['id'], gdf_copy['POI_cates']):
        POI_cates = cates_str2list(POI_cates_str)
        if len(POI_cates) == 0:
            continue
        for cate in POI_cates:
            if cate in all_cates:
                cate2areas[cate].append(area_id)


    walk_scores = []
    agent_cate_dist = pd.DataFrame(index=agentdf['AgentID'], columns=all_cates)
    for agent_id in tqdm(agentdf['AgentID'], desc="Evaluating plan"):
        cur_agent = agentdf[agentdf['AgentID'] == agent_id]
        agent_location = cur_agent[['Location_x', 'Location_y']].iloc[0]
        loc = Point(agent_location['Location_x'], agent_location['Location_y'])

        cate_scores = []
        for cate in all_cates:
            areas_with_cate = cate2areas[cate]
            if len(areas_with_cate) == 0:
                min_distance = 100000.0
            else:
                min_distance = agent_area_dist.loc[agent_id, areas_with_cate].min()
            agent_cate_dist.loc[agent_id, cate] = min_distance
            if min_distance < walkscore_min_dist:
                score = 1
            elif min_distance > walkscore_max_dist:
                score = 0
            else:
                score = (min_distance - walkscore_max_dist)/(walkscore_min_dist - walkscore_max_dist)
            cate_scores.append(score)

        agent_score = np.mean(cate_scores)
        walk_scores.append(agent_score)
    walk_score = np.mean(walk_scores)
    return walk_score, walk_scores, agent_cate_dist

def calculate_service_access(gdf, agentdf, agent_area_dist, evaluation_configs, agent_cate_dist=None):
    distance_15min = evaluation_configs['distance_15min']

    public_service = ['shopping', 'office', 'education', 'medical', 'recreation']
    
    gdf_copy = gdf.copy()
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].fillna('')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('educational facility', 'education')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('school', 'education')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('medical facility', 'medical')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('hospital', 'medical')

    access_rates = []
    for agent_id in agentdf['AgentID']:
        if agent_cate_dist is not None:
            access_service = [x for x in public_service if agent_cate_dist.loc[agent_id,x] < distance_15min]
        else:
            agent_distances = agent_area_dist.loc[agent_id]
            area_15min = agent_distances[agent_distances < distance_15min].index.tolist()
            gdf_within_distance = gdf_copy[gdf_copy['id'].isin(area_15min)]

            tmp = []
            for POI_cates_str in gdf_within_distance['POI_cates'].tolist():
                POI_cates = cates_str2list(POI_cates_str)
                tmp.extend(POI_cates)
            access_service = list(set(tmp))
            access_service = [x for x in access_service if x in public_service]
            access_service = [x for x in public_service if x in access_service]


        rate = len(access_service) / len(public_service)
        access_rates.append(rate)
    access_rate = np.mean(access_rates)
    return access_rate, access_rates

def calculate_need_satisfaction_rate(gdf, agentdf, agent_area_dist, evaluation_configs, agent_cate_dist=None):
    distance_15min = evaluation_configs['distance_15min']

    gdf_copy = gdf.copy()
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].fillna('')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('educational facility', 'education')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('school', 'education')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('medical facility', 'medical')
    gdf_copy['POI_cates'] = gdf_copy['POI_cates'].str.replace('hospital', 'medical')

    meet_need_cnt = 0
    total_need_cnt = 0
    meet_special_need_cnt = 0
    total_special_need_cnt = 0
    special_agent_cnt = 0
    satisfactions = []
    for agent_id in agentdf['AgentID']:
        cur_agent = agentdf[agentdf['AgentID'] == agent_id]
        agent_need = eval(cur_agent['Need'].item())
        if agent_cate_dist is not None:
            meet_need = [x for x in agent_need if agent_cate_dist.loc[agent_id,x] < distance_15min]
        else:
            agent_distances = agent_area_dist.loc[agent_id]
            area_15min = agent_distances[agent_distances < distance_15min].index.tolist()
            gdf_within_distance = gdf_copy[gdf_copy['id'].isin(area_15min)]
        
            tmp = []
            for POI_cates_str in gdf_within_distance['POI_cates'].tolist():
                POI_cates = cates_str2list(POI_cates_str)
                tmp.extend(POI_cates)
            tmp = list(set(tmp))
            meet_need = [x for x in tmp if x in agent_need]
        
        meet_need_cnt += len(meet_need)
        total_need_cnt += len(set(agent_need))

        sat = len(meet_need)/len(set(agent_need))
        satisfactions.append(sat)
        
        # special groups
        if not pd.isna(cur_agent['Special'].item()):
            special_agent_cnt += 1
            meet_special_need_cnt += len(meet_need)
            total_special_need_cnt += len(set(agent_need))

    satisfaction_rate = meet_need_cnt/total_need_cnt
    special_satisfaction_rate = meet_special_need_cnt/total_special_need_cnt
#     print(meet_need_cnt, meet_special_need_cnt)
    return satisfaction_rate, special_satisfaction_rate, satisfactions

def evaluate(gdf, agentdf, agent_area_dist, evaluation_configs):
    """Return and print the seven plan metrics; equality is defined as 1 - Gini."""
    walk_score, walk_scores, agent_cate_dist = calculate_walk_score(
        gdf, agentdf, agent_area_dist, evaluation_configs
    )
    service_agent, services = calculate_service_access(
        gdf, agentdf, agent_area_dist, evaluation_configs,
        agent_cate_dist=agent_cate_dist,
    )
    sat, spe_sat, satisfactions = calculate_need_satisfaction_rate(
        gdf, agentdf, agent_area_dist, evaluation_configs,
        agent_cate_dist=agent_cate_dist,
    )

    walk_equality = 1 - gini_coefficient(walk_scores)
    service_equality = 1 - gini_coefficient(services)
    satisfaction_equality = 1 - gini_coefficient(satisfactions)
    result = [walk_score, service_agent, sat, spe_sat,
              walk_equality, service_equality, satisfaction_equality]
    for name, value in zip(METRIC_NAMES, result):
        print(f'{name}: {value:.3f}')
    return result
