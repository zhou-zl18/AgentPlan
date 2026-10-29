"""Map and resident-profile loading, distance matrices, and initial land use."""
import os
import geopandas as gp
import pandas as pd
from shapely.geometry import Point
from tqdm import tqdm
from .spatial import calculate_direction, get_area_from_location


def load_experiment_data(filepath):
    # load map
    filename = os.path.join(filepath,"basemap.geojson")
    gdf = gp.read_file(filename)
    gdf['POI_cates'] = gdf['POI_original'].copy()
    print(gdf.shape)

    # load agents
    agentdf = pd.read_excel(os.path.join(filepath,'Agent_Profile_1000.xlsx'))
    print(agentdf.shape)

    # get agents' address area

    agentdf['address_area'] = agentdf.apply(lambda row: get_area_from_location(gdf, Point(row['Location_x'], row['Location_y'])), axis=1)


    # 计算每个agent到每个area的边界的距离
    non_resi_gdf = gdf[gdf['type']!='residential']
    agent_area_dist = pd.DataFrame(index=agentdf['AgentID'], columns=non_resi_gdf['id'])
    agent_area_direction = pd.DataFrame(index=agentdf['AgentID'], columns=non_resi_gdf['id'])

    for agent_id in tqdm(agentdf['AgentID'].tolist()):
        cur_agent = agentdf[agentdf['AgentID'] == agent_id]
        agent_location = cur_agent[['Location_x', 'Location_y']].iloc[0]
        loc = Point(agent_location['Location_x'], agent_location['Location_y'])
        dist = non_resi_gdf['geometry'].apply(lambda polygon: loc.distance(polygon)).tolist()
        agent_area_dist.loc[agent_id, :] = dist
        direction = non_resi_gdf['geometry'].apply(lambda polygon: calculate_direction(loc, polygon.centroid)).tolist()
        agent_area_direction.loc[agent_id, :] = direction
    return gdf, agentdf, agent_area_dist, agent_area_direction


def load_evaluation_data(filepath):
    filename = os.path.join(filepath, "basemap.geojson")
    gdf = gp.read_file(filename)
    gdf['POI_cates'] = gdf['POI_original'].copy()
    gdf['POI_cates'] = gdf['POI_cates'].fillna('')

    # get agents' address area
    # load agents
    agentdf=pd.read_excel(os.path.join(filepath,'Agent_Profile_1000.xlsx'))
    print("user:",agentdf.shape)
    # agentdf.head()
    agentdf['address_area'] = agentdf.apply(lambda row: get_area_from_location(gdf, Point(row['Location_x'], row['Location_y'])), axis=1)

    # 计算每个agent到每个area的距离
    non_resi_gdf = gdf[gdf['type']!='residential']
    agent_area_dist = pd.DataFrame(index=agentdf['AgentID'], columns=non_resi_gdf['id'])

    for agent_id in tqdm(agentdf['AgentID'].tolist()):
        cur_agent = agentdf[agentdf['AgentID'] == agent_id]
        agent_location = cur_agent[['Location_x', 'Location_y']].iloc[0]
        loc = Point(agent_location['Location_x'], agent_location['Location_y'])
        dist = non_resi_gdf['geometry'].apply(lambda polygon: loc.distance(polygon)).tolist()
        agent_area_dist.loc[agent_id, :] = dist
    return gdf, agentdf, agent_area_dist
