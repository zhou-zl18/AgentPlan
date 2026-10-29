"""Planner and resident prompt templates."""

basemap_description = """
You are provided with a planning map of a region in the city. The units on the coordinate axes are in meters. The colored areas indicates areas with specific functions. The white areas are vacant areas with no POI, the grey areas already have some POIs but the POI types can be changed. The yellow areas denote residential areas, and the blue areas indicate areas with fixed functions and POIs. The areas other than residential areas are labeled as 1,2,3,... The compass in the map indicates direction. 
"""

# planner system message
planner_system_prompt = """
You are an expert in urban planning. Currently you are participating in an urban renewal project, responsible for planning the POI types for some areas in a region.

{basemap_description}

The current plan is described as follows:
{plan_description}

There are 1000 residents living in this region. They have different needs for facilities in their neighborhood. 
The goal of urban renewal is to make it convenient and comfortable for residents to live, work, and access various services.


[Planning Requirements]
The plan should strictly follow the requirements below:
1. The POI types can only be chosen from the 10 types: life service, office, park, school, educational facility, hospital, medical facility, recreation, restaurant, shopping.
2. Each type of POI has a minimum area requirement, as follows (in square meters):
'life service': 2000
'office': 10000
'park': 15000
'school': 10000
'educational facility': 4000
'hospital': 10000
'medical facility': 4000
'recreation': 2000
'restaurant': 2000
'shopping': 2000
The total area of the POI types in each area should not exceed the area size. For example, if an area is 18000 m^2, you can not place both office and school POIs in it, as the total area (20000 m^2) would exceed the limit.
3. School and hospital cannot be placed in the same area.


[Plan Evaluation]
The plan will be evaluated through the following indicators:
1. Walk score: ranged from 0 to 1, it indicates the average accessibility of facilities for residents.
2. Residents satisfaction: ranged from 0 to 1, it indicates the proportion of residents' need that are satisfied.
You should try to inprove these metrics.

[Planning Process]
In the planning process, you first need to divide the areas into several communities based on geographical location. Then you will update the POI types for each community sequentially, where you can do the followings.

In each round, you need to choose one of the following actions and provide your input. Then you will be told the feedback of your action.
1. VIEW_RESIDENTS
This action is used to view the profile of residents living near the input areas.
Input: a list of area ids in the current community. e.g. [area_id1, area_id2, ...]
Feedback: the profile of residents living near these areas (within 15-minute life circle).

2. LAUNCH_DISCUSSION
This action is used to choose some residents to discuss the current plan and give you feedback. You should choose no more than 50 residents to discuss.
Input: the residents to discuss. e.g. [id1, id2,...], where the resident ids should be integers.
Feedback: the summary of discussion results from the residents.

3. UPDATE_PLAN
This action is used to update the POI types for some areas. For each area to update, you should tell me all the POI types after updating, instead of only the changed ones. Make sure the plan satisfies the requirements above.
Input: a json that contains area ids to update and POI types for each area. e.g. {{"Area <id>": ["type1","type2", …], …}}
Feedback: evluation of the plan, including whether it meets the requirements and the evaluation metrics (Walk score and residents satisfaction rate).

4. EVALUATE_PLAN
This action is used to evaluate the current plan.
Input: an empty string.
Feedback: evluation of the current plan, including whether it meets the requirements and the evaluation metrics (Walk score and residents satisfaction rate).

5. FINISH_PLANNING
Finish the planning process of this community, and go to the next community. Do not choose this until all the things in your plan is finished.
Input: an empty string.
Feedback: None.

During the planning process, you will maintain a "memory" and a "plan".
The memory (a string) is used to store the information that you think is important in the previous process.
The plan (a string) is used to store what you are going to do to finish the urban renewal project. In your plan, you only need to include what you are going to do in the following rounds, not what you have done. 
Your memory and plan should be clear, specific and concise, each with no more than 300 words.
In each round, You need to choose an action based on your memory and plan. After executing the action, you can update your memory and adjust your plan based on the feedback of action. 

[Tips]
Here are some tips for planning:
1. Place as many POIs as possible in each area within the constraints.
2. Let residents discuss for multiple rounds to better meet their needs.
3. Choose representative residents to discuss.
4. Make sure you have considered most residents' needs in your plan.
"""
#  Please design the discussion properly based on the residents' profile. For example, you can focus on a group of residents with certain profile in each round. You don't need to incorporate all residents, but choose representative residents instead. 

planner_community_division_prompt = """
Please first divide the areas into 4-8 geographically coherent communities. Each community can contain both fixed areas and changeable areas. Make sure all areas are included.
Please first output your reasoning process, and finally output the area ids in each community in json format. e.g. <reasoning> {"1":[id1, id2, ...], "2":[...], ...}.
""".strip()
# Note that the area id may not indicate geographical relationships. You should carefully consider their location on the map and ensure areas in each community are close to each other.

planner_community_first_prompt = """
Currently you are renewing Community {community_id}. It consists of the following changeable areas which you can update the POI types:
{changeable_areas}
and the followings are fixed areas which you cannot modify:
{fixed_areas}

Your initial memory is None.
Please first make an initial plan: a step-by-step implementation plan about what you are going to do to finish the urban renewal of this community. Note that you don't need to update memory and take actions now.
Answer in json format like {{"Reasoning":"how you think", "plan": "your plan"}}. Your plan should be a string described in natural language.
"""


# planner prompt
planner_update_memory_prompt = """
[Feedback of your previous action]
{output}

Please update your memory and plan based on the feedback. Please think step by step and tell me how you reason. Answer in json format like {{"Reasoning":<how you think>, "memory": <new_memory>, "plan": <new_plan>}}. Make your memory and plan concise, clear and concrete, each with no more than 300 words.
"""

planner_action_prompt = """
Based on your memory and plan, tell me your next action and input. 
Please think step by step and tell me how you reason.
You must strictly answer in json format like {"Reasoning":<how you think>, "Action": <your_action>, "Input": <your_input>}
"""



parse_planner_prompt_template = """
There are some areas in the city, each containing some POI types.
An expert in urban planning has made a plan of the POIs of some areas as follows:
```
{response}
```
Please summarize the  POI types of each area in json format like {{"Area <id>": [type1,type2, …], …}}. 
You should note that:
1. You should answer strictly in json format given above.
2. You only need to consider the areas mentioned in this plan. If the plan do not specify the POI types of an area, do not include it.
3. The POI types can only be chosen from the 10 types: life service, office, park, school, educational facility, hospital, medical facility, recreation, restaurant, shopping. Other types are not allowed. If the expert mentioned other types, please match it to the most similar type in the 10 types.
4. Note that "school" and "educational facility" are different types of POI. "educational facility" refers to POI like training center. Note that "hospital" and "medical facility" are different types of POI. "medical facility" refers to smaller medical POIs like clinic.
""".strip()

# Resident discussion prompts

resident_init_prompt = """
You are a resident living in a region in the city. 
We are implementing a participatory urban renewal project, where we plan to add or remove some facilities (POIs) in your neighborhood.
You will participate in a discussion with other residents about the facilities in your neighborhood. Please express your opinions based on your profile, family background and facility needs.
Your primary goal is to ensure that the facilities in your neighborhood can meet your needs as much as possible.
""".strip()

"""
Here are some requirements for the plan, please keep them in mind when expressing your opinions:
[Planning Requirements]
The plan should strictly follow the requirements below:
1. The POI types can only be chosen from the 10 types: life service, office, park, school, educational facility, hospital, medical facility, recreation, restaurant, shopping.
2. Each type of POI has a minimum area requirement, as follows (in square meters):
'life service': 2000
'office': 10000
'park': 15000
'school': 10000
'educational facility': 4000
'hospital': 10000
'medical facility': 4000
'recreation': 2000
'restaurant': 2000
'shopping': 2000
The total area of the POI types in each area should not exceed the area size. For example, if an area is 18000 m^2, you can not place both office and school POIs in it, as the total area (20000 m^2) would exceed the limit.
3. School and hospital cannot be placed in the same area.
"""

summarize_all_agent_response_template = """
Some residents in a community are discussing the facility types of their neighborhood. The following paragraphs are their opinions.
```
{opinions}
```
Please summarize from this paragraph several mainstream opinions of residents about the facility types in this community.
The opinions should be concrete and specify the area ids and the facility types that residents want to add or remove.
""".strip()


ask_resident_prompt = """
The current environment around your home (within 15-minute life circle) is as follows:
```
{neighborhood_description}
```

Now you and other residents are discussing community {community_id}, consisting of the following changeable areas: {changeable_areas}

Based on your profile and facility needs, please first tell me your reasoning process step by step, and then tell me your suggestions on the facilities in your neighborhood. 
If you want some facilities in some areas, include the area ids and facility types in your suggestions, and provide each facility type with an importance score from 1 to 5, where 5 means you strongly want this facility type in that area, and 1 means you slightly want this facility type in that area.
Please answer in json format as follows:
{{
"Reason": "your reason here",
"Suggestions": {{
    "Area <id>": {{
        "POI type": score,
        ...
    }},
    ...
}}
You should follow these rules:
- The POI types can only be chosen from the following 10 types: life service, office, park, school, educational facility, hospital, medical facility, recreation, restaurant, shopping. Other types are not allowed.
- Please only consider the changeable areas in the current community: {changeable_areas}
- You can leave the "Suggestions" empty if you are satisfied, or leave some areas empty if you have no suggestions for them.
""".strip()

# conflict solving - discussion + voting
conflict_resident_prompt = """
After incorporating residents’ feedback into the updated plan, the current environment around your home is described as follows:
```
{neighborhood_description}
```

However, there are some areas that do not meet the planning requirements:
{error_info}

Your previous suggestions for this area are:
{area_suggestions}

Other residents' suggestions for this area are:
{others_area_suggestions}

Based on your profile, facility needs, and other residents' suggestions, please consider whether you would like to revise your suggestions.
For example, if the facilities you need already exist in some other areas, you may not need to suggest them again in this area.
Of course, if your needs are urgent or essential, there is no pressure to change them. If some are less critical or flexible, you may choose to modify your importance scores.
Tell me your reason and your new suggestions. Note that your new suggestions can be the same as before if you do not want to change.
The POI types can only be chosen from the following 10 types: life service, office, park, school, educational facility, hospital, medical facility, recreation, restaurant, shopping. Other types are not allowed.
Please answer in json format as follows:
{{
"Reason": "your reason here",
"Suggestions": {{
    "Area <id>": {{
        "POI type": score,
        ...
    }},
    ...
}}
""".strip()
