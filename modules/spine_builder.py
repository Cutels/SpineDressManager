#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spine JSON 合成模块
"""

import json
import shutil
from pathlib import Path
from collections import OrderedDict

class SpineBuilder:
    def __init__(self, db):
        self.db = db
        
    def convert_skinnedmesh_to_mesh(self, attach_data, slot_name=''):
        """将 skinnedmesh 转换为 mesh，保留骨骼权重"""
        if attach_data.get('type') != 'skinnedmesh':
            return attach_data
        
        vertices = attach_data.get('vertices', [])
        
        # 检查是否包含骨骼权重
        has_weights = False
        if len(vertices) > 0:
            first_val = vertices[0]
            if isinstance(first_val, (int, float)) and 0 < first_val < 20:
                has_weights = True
        
        if not has_weights:
            return {
                "type": "mesh",
                "uvs": attach_data.get('uvs', []),
                "triangles": attach_data.get('triangles', []),
                "vertices": vertices,
                "hull": attach_data.get('hull', 0)
            }
        
        # 转换带权重的顶点
        converted_vertices = []
        i = 0
        while i < len(vertices):
            bone_count = int(vertices[i])
            converted_vertices.append(bone_count)
            i += 1
            
            for _ in range(bone_count):
                bone_index = int(vertices[i])
                x = vertices[i + 1]
                y = vertices[i + 2]
                weight = vertices[i + 3]
                converted_vertices.extend([bone_index, x, y, weight])
                i += 4
        
        result = {
            "type": "mesh",
            "uvs": attach_data.get('uvs', []),
            "triangles": attach_data.get('triangles', []),
            "vertices": converted_vertices,
            "hull": attach_data.get('hull', 0)
        }
        
        if 'edges' in attach_data:
            result['edges'] = attach_data['edges']
        if 'width' in attach_data:
            result['width'] = attach_data['width']
        if 'height' in attach_data:
            result['height'] = attach_data['height']
        
        return result

    def find_bone_by_slot_name(self, slot_name, bones):
        """根据插槽名称找到对应的骨骼"""
        # 移除前缀
        base_name = slot_name
        for prefix in ['BaseBody_', 'Pants_', 'Shoes_', 'Tops_']:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]
                break
        
        # 移除后缀
        for suffix in ['_Front', '_Back', '_Left', '_Right']:
            if base_name.endswith(suffix):
                base_name = base_name[:-len(suffix)]
                break
        
        # 特殊映射 - 按优先级排序（更具体的在前）
        special_mappings = {
            'HeadDress': 'hairdresser',  # 头饰优先于 Hair
            'Head': 'head',
            'Eyeball': 'eye',
            'Eyeliner': 'eye',
            'Eyeskin': 'eye',
            'White_Of_Eyes': 'eye',
            'Eyebrow': 'eyebrow',
            'Mouth': 'mouth',
            'Nose': 'nose',
            'Fringe': 'head',
            'Hair': 'head',
            'Tops': 'spine',
            'Belt': 'belt',
            'Calf': 'calf',
            'Thigh': 'thigh',
            'Foot': 'foot',
            'Upperarm': 'upperarm',
            'Forearm': 'forearm',
            'Hand': 'hand',
            'Shoes': 'foot',
            'Pants': 'pelvis'
        }
        
        # 查找匹配 - 优先精确匹配，再模糊匹配
        slot_lower = slot_name.lower()
        
        # 首先尝试精确匹配（去除前后缀后的base_name）
        base_lower = base_name.lower()
        for key, value in special_mappings.items():
            if base_lower == key.lower():
                # 检查左右
                if '_Left' in slot_name:
                    value = value + '_left'
                elif '_Right' in slot_name:
                    value = value + '_right'
                
                # 在骨骼列表中查找
                for bone in bones:
                    if value.lower() in bone['name'].lower():
                        return bone['name']
        
        # 如果没有精确匹配，再尝试模糊匹配
        for key, value in special_mappings.items():
            if key.lower() in slot_lower:
                # 检查左右
                if '_Left' in slot_name:
                    value = value + '_left'
                elif '_Right' in slot_name:
                    value = value + '_right'
                
                # 在骨骼列表中查找
                for bone in bones:
                    if value.lower() in bone['name'].lower():
                        return bone['name']
        
        return 'root'

    def merge_action_to_role(self, role_data, action_path):
        """将 action.json 合并到 role.json - 参考 merge_all_dress.py 简化版"""
        with open(action_path, 'r', encoding='utf-8') as f:
            action_data = json.load(f)
        
        # 合并骨骼（不重复）
        existing_bone_names = {b['name'] for b in role_data.get('bones', [])}
        for bone in action_data.get('bones', []):
            if bone['name'] not in existing_bone_names:
                role_data['bones'].append(bone)
        
        # 合并插槽（不重复）
        existing_slot_names = {s['name'] for s in role_data.get('slots', [])}
        for slot in action_data.get('slots', []):
            if slot['name'] not in existing_slot_names:
                role_data['slots'].append(slot)
        
        # 合并 skins
        skins = role_data.setdefault('skins', {}).setdefault('default', {})
        action_skins = action_data.get('skins', {})
        
        for slot_name, slot_data in action_skins.items():
            if isinstance(slot_data, dict):
                if slot_name not in skins:
                    skins[slot_name] = {}
                for attach_name, attach_data in slot_data.items():
                    if isinstance(attach_data, dict):
                        converted = self.convert_skinnedmesh_to_mesh(attach_data, slot_name)
                        skins[slot_name][attach_name] = converted
        
        # 合并动画 - 直接复制（参考 merge_all_dress.py）
        if 'animations' not in role_data:
            role_data['animations'] = {}
        for anim_name, anim_data in action_data.get('animations', {}).items():
            role_data['animations'][anim_name] = anim_data
        
        return role_data

    def build_character(self, role_path, selected_items, output_dir, include_animation=False, animation_path=None):
        """构建角色"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载 role.json
        with open(role_path, 'r', encoding='utf-8') as f:
            role_data = json.load(f)
        
        # 确保基本结构
        if 'skins' not in role_data:
            role_data['skins'] = {}
        if 'default' not in role_data['skins']:
            role_data['skins']['default'] = {}
        
        skins = role_data['skins']['default']
        bones = role_data.get('bones', [])
        slots = role_data.get('slots', [])
        slot_map = {s['name']: s for s in slots}
        
        total_images = 0
        
        # 合并选中的服装
        for md5_hash, item_data in selected_items.items():
            clothing_type = item_data['type']
            folder_path = Path(item_data['path'])
            dress_path = folder_path / "dress.json"
            
            if not dress_path.exists():
                continue
            
            with open(dress_path, 'r', encoding='utf-8') as f:
                dress_data = json.load(f)
            
            # 合并骨骼
            existing_bones = {b['name'] for b in role_data.get('bones', [])}
            for bone in dress_data.get('bones', []):
                if bone['name'] not in existing_bones:
                    role_data['bones'].append(bone)
                    existing_bones.add(bone['name'])
                    bones = role_data['bones']
            
            # 处理附件
            attachments = dress_data.get('attachments', {})
            
            # BaseBody 特殊处理 - 严格过滤手部变体
            if clothing_type == "BaseBody":
                original_count = len(attachments)
                filtered_attachments = {}
                for slot_name, slot_attachments in attachments.items():
                    # 严格匹配：只保留纯 Hand_Left 和 Hand_Right
                    if slot_name == 'Hand_Left' or slot_name == 'Hand_Right':
                        # 进一步过滤附件，只保留纯 Hand_Left/Hand_Right
                        filtered_slot_attach = {}
                        for attach_name, attach_data in slot_attachments.items():
                            # 严格匹配附件名
                            if attach_name == 'Hand_Left' or attach_name == 'Hand_Right':
                                filtered_slot_attach[attach_name] = attach_data
                        if filtered_slot_attach:
                            filtered_attachments[slot_name] = filtered_slot_attach
                    elif slot_name.startswith('Hand_') and slot_name not in ['Hand_Left', 'Hand_Right']:
                        # 跳过所有其他 Hand_ 开头的插槽（如 Hand_Right_Front4, Hand_Left4 等）
                        continue
                    else:
                        # 其他插槽正常保留（包括 arm, body 等）
                        filtered_attachments[slot_name] = slot_attachments
                attachments = filtered_attachments
            
            for slot_name, slot_attachments in attachments.items():
                # 确保插槽存在
                if slot_name not in slot_map:
                    correct_bone = self.find_bone_by_slot_name(slot_name, bones)
                    new_slot = {
                        'name': slot_name,
                        'bone': correct_bone,
                        'attachment': list(slot_attachments.keys())[0] if slot_attachments else None
                    }
                    role_data['slots'].append(new_slot)
                    slot_map[slot_name] = new_slot
                else:
                    slot = slot_map[slot_name]
                    if slot.get('bone') == 'root':
                        correct_bone = self.find_bone_by_slot_name(slot_name, bones)
                        slot['bone'] = correct_bone
                
                # 添加附件
                if slot_name not in skins:
                    skins[slot_name] = {}
                
                for attach_name, attach_data in slot_attachments.items():
                    converted = self.convert_skinnedmesh_to_mesh(attach_data, slot_name)
                    skins[slot_name][attach_name] = converted
                    
                    if slot_name in slot_map:
                        slot_map[slot_name]['attachment'] = attach_name
            
            # 复制图片
            for img_file in folder_path.glob("*.png"):
                # BaseBody 特殊处理：过滤 Hand_ 开头的变体图片（只保留 Hand_Left/Right）
                if clothing_type == "BaseBody":
                    img_name = img_file.stem
                    # 跳过 Hand_ 开头但不是 Hand_Left/Right 的图片
                    if img_name.startswith('Hand_') and img_name not in ['Hand_Left', 'Hand_Right']:
                        continue
                
                dest = output_dir / img_file.name
                shutil.copy2(img_file, dest)
                total_images += 1
        
        # 合并动画
        if include_animation and animation_path and Path(animation_path).exists():
            role_data = self.merge_action_to_role(role_data, animation_path)
            # 复制动画图片
            anim_dir = Path(animation_path).parent
            for img_file in anim_dir.glob("*.png"):
                dest = output_dir / img_file.name
                shutil.copy2(img_file, dest)
                total_images += 1
        
        # 更新 skeleton 信息
        if 'skeleton' not in role_data:
            role_data['skeleton'] = {}
        role_data['skeleton']['spine'] = "4.2.0"
        role_data['skeleton']['hash'] = ""
        
        # 保存统计数据（在重新排序前）
        bones_count = len(role_data.get('bones', []))
        slots_count = len(role_data.get('slots', []))
        attachments_count = sum(len(v) for v in skins.values())
        
        # 重新排序字段，确保 skeleton 在最前面（Spine要求）
        ordered_data = OrderedDict()
        ordered_data['skeleton'] = role_data.pop('skeleton', {})
        
        # 按 Spine 标准顺序添加其他字段
        field_order = ['bones', 'slots', 'ik', 'transform', 'path', 'skins', 'animations']
        for field in field_order:
            if field in role_data:
                ordered_data[field] = role_data.pop(field)
        
        # 添加剩余字段
        for key, value in role_data.items():
            ordered_data[key] = value
        
        # 保存 JSON
        output_json = output_dir / f"{output_dir.name}.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(ordered_data, f, indent=2, ensure_ascii=False)
        
        return {
            'json_path': str(output_json),
            'total_images': total_images,
            'bones_count': bones_count,
            'slots_count': slots_count,
            'attachments_count': attachments_count
        }

if __name__ == "__main__":
    from database import ClothingDatabase
    
    db = ClothingDatabase()
    builder = SpineBuilder(db)
    
    print("SpineBuilder 模块已加载")
