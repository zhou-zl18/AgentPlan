"""Resident and planner agents."""
import copy
import pandas as pd
from .llm import get_completion, encode_image
from .prompts import resident_init_prompt

class Resident:
    def __init__(self, info, gdf, agent_area_dist, agent_area_direction, distance_15min, model='gpt-4o-mini'):
        self.id = info['AgentID'] - 1
        self.model = model
        # Profile
        self.special = info['Special'] if not pd.isna(info['Special']) else None
        self.need = eval(info['Need'])
        tmp = f"""[Resident-{self.id}]:\n"""
        for k,v in info.items():
            if k in ['AgentID','Special','Description','Location_x','Location_y','Need','address_area','Address']:
                continue
            tmp += f"""{k}:{v}\n"""
        
        if self.special is not None:
            tmp += f"Background: {self.special}\n"
        self.profile = tmp

        # environment
        self.address_area = info['address_area']
        self.area2distance = self.get_area2distance(agent_area_dist)
        self.area2direction = self.get_area2direction(agent_area_direction)
        
        changeable_areas = gdf[gdf['type'].isin(['vacant','changeable'])]['id'].tolist()
        fixed_areas = gdf[gdf['type'].isin(['fixed'])]['id'].tolist()
        self.area_15min = [area for area, distance in self.area2distance.items() if distance<=distance_15min and area in changeable_areas] 
        self.fix_area_15min = [area for area, distance in self.area2distance.items() if distance<=distance_15min and area in fixed_areas] 

        # chat
        self.description = info['Description'] + '\nYour facility needs are: ' + ', '.join(self.need) + '.'
        system_prompt = self.description + '\n' + resident_init_prompt
        self.messages = [
                {"role": "system", "content": system_prompt},
            ]

    def __repr__(self):
        return f'Resident {self.id}'
    
    def get_area2distance(self, agent_area_dist):
        agent_id = self.id + 1
        area_dist = agent_area_dist.loc[agent_id, :]
        area2distance = {}
        for area_id, dist in area_dist.items():
            area2distance[area_id] = int(dist)
        return area2distance

    def get_area2direction(self, agent_area_direction):
        area2direction = {}
        for area_id, direction in agent_area_direction.loc[self.id+1, :].items():
            area2direction[area_id] = direction
        return area2direction
    
    def get_areas_description(self, gdf, area_ids):
        changeable_areas_description = ''
        fixed_areas_description = ''
        for area_id in area_ids:
            cur_area = gdf[gdf['id'] == area_id].iloc[0]
            # area类型
            area_type = cur_area['type']
            if area_type == 'residential':
                continue
            POI_cates = cur_area['POI_cates']  
            # area面积
            area_size = int(cur_area['area'])
            dist = int(self.area2distance[area_id])
            direction = self.area2direction[area_id]
            if area_type in ['changeable', 'vacant']:
                tmp = f"""Area {area_id} ({area_size} m^2, {dist} meters {direction}): {POI_cates}.\n"""
                changeable_areas_description += tmp
            elif area_type == 'fixed':
                tmp = f"""Area {area_id} ({area_size} m^2, {dist} meters {direction}): {POI_cates}.\n"""
                fixed_areas_description += tmp
            else:
                raise ValueError(f'Invalid area type: {area_type}')
            
        if len(changeable_areas_description) == 0:
            changeable_areas_description = 'None.'
        if len(fixed_areas_description) == 0:
            fixed_areas_description = 'None.'
        descriptions = "Here is the information of areas near your home, including their sizes, distance and direction to your home, and facility types. "
        descriptions += "The following areas are changeable:\n" + changeable_areas_description + "\nThe following areas are fixed and the facilities in them cannot be changed:\n" + fixed_areas_description
        return descriptions
    
    def append_message(self, prompt=None, response=None):
        if prompt is not None:
            self.messages.append({"role": "user", "content": prompt})
        if response is not None:
            self.messages.append({"role": "assistant", "content": response})

    def clear_chat_history(self): # keep only system message
        self.messages = self.messages[:1]
    
    def chat(self, message, temperature=0):
        self.messages.append({"role": "user", "content": message})
        response = get_completion(self.messages, model=self.model, temperature=temperature)
        self.messages.append({"role": "assistant", "content": response})
        return response
    
    def chat_wo_update(self, message, temperature=0):
        tmp_message=copy.deepcopy(self.messages)
        tmp_message.append({"role": "user", "content": message})
        response = get_completion(tmp_message, model=self.model, temperature=temperature)
        return response

class Planner:
    def __init__(self, system_prompt, image_path, model="gpt-4o"):
        
        print('Initialize planner')
        self.model = model
        self.image_path = image_path
        self.system_prompt = system_prompt

        # memory
        self.memory = ''
        self.plan = ''

        # chat
        self.chat_history = []
        self.action_history = []
        self.max_message_length = 10

        
    def update_memory(self, message):
        self.memory = message
        
    def update_plan(self, message):
        self.plan = message

    def update_action_history(self, action, input, feedback):
        record = {
            'action': action,
            'input': input,
            'feedback': feedback
        }
        self.action_history.append(record)
        

    def create_prompt(self, prompt):
        action_history = '[Your recent actions]\n'
        start_idx = max(0, len(self.action_history) - 10)
        for record in self.action_history[start_idx:]:
            action_history += f"Action: {record['action']}\nInput: {record['input']}\nFeedback: {record['feedback']}\n"

        full_prompt = action_history + '\n[Your current memory]\n' + self.memory + '\n[Your current plan]\n' + self.plan + '\n' + prompt

        return full_prompt
    

    def chat(self, prompt, temperature=0, with_history=True):
        if with_history:
            full_prompt = self.create_prompt(prompt)
        else:
            full_prompt = prompt
            
        base64_image = encode_image(self.image_path)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
            "role": "user", 
            "content": [
                    {"type": "text", "text": full_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                ],
            }
        ]
        response = get_completion(messages, model=self.model, temperature=temperature)
        self.chat_history.append({"role": "user", "content": prompt})
        self.chat_history.append({"role": "assistant", "content": response})
        return response
