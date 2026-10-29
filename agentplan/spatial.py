"""Shared geometry and direction helpers."""
import math
import geopandas as gp
from shapely.geometry import Point

def find_agents_within_distance(gdf, agentdf, area_id, distance) -> list: # find agents within certain distance to area_id's boundary
    polygon = gdf[gdf['id'] == area_id].geometry.iloc[0]
    buffer = polygon.buffer(distance)
    
    tmp_agentdf = agentdf.copy()
    tmp_agentdf['geometry'] = tmp_agentdf.apply(lambda row: Point(row['Location_x'], row['Location_y']), axis=1)
    geo_agentdf = gp.GeoDataFrame(tmp_agentdf, geometry='geometry')
    agents_within_distance = geo_agentdf[geo_agentdf.within(buffer)]

    return agents_within_distance['AgentID'].tolist()

def find_areas_within_distance(gdf, agentdf, agent_id, distance) -> list: # find areas within certain distance to agent_id's location
    agent_location = agentdf[agentdf['AgentID'] == agent_id][['Location_x', 'Location_y']].iloc[0]
    agent_point = Point(agent_location['Location_x'], agent_location['Location_y'])
    buffer = agent_point.buffer(distance)

    # do not include residential areas
    target_areas = gdf[(gdf['type'] != 'residential')]
    
    areas_within_distance = target_areas[target_areas.geometry.intersects(buffer)]

    return areas_within_distance['id'].tolist()

def calculate_distance_and_direction(point1, point2): # point2 is at which direction of point 1
    distance = point1.distance(point2)

    # 计算方位角（角度）
    dx = point2.x - point1.x
    dy = point2.y - point1.y
    angle = math.atan2(dy, dx) * 180 / math.pi  # 将弧度转换为角度
    # 将角度映射到8个方位
    directions = ["west","southwest","south","southeast","east","northeast","north","northwest"]
    index = round((angle + 180) / 45) % 8
    direction = directions[index]

    return distance, direction

def calculate_direction(point1, point2): # point2 is at which direction of point 1
    # 计算方位角（角度）
    dx = point2.x - point1.x
    dy = point2.y - point1.y
    angle = math.atan2(dy, dx) * 180 / math.pi  # 将弧度转换为角度
    # 将角度映射到8个方位
    directions = ["west","southwest","south","southeast","east","northeast","north","northwest"]
    index = round((angle + 180) / 45) % 8
    direction = directions[index]

    return direction

def get_area_from_location(gdf, loc):
    for index, row in gdf.iterrows():
        if row['geometry'].contains(loc):
            return row['id']
    return None

def get_distance_to_community(gdf, area_id: int, community_area_ids: list):
    community_gdf = gdf[gdf['id'].isin(community_area_ids)]
    area_geom = gdf[gdf['id'] == area_id].geometry.values[0]
    dists = community_gdf.apply(lambda x: area_geom.distance(x['geometry']), axis=1).tolist()
    return min(dists)
