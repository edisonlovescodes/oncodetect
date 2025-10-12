import os
import pydicom
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from tqdm import tqdm

RAW_DATA_PATH = 'raw_data/LIDC-IDRI' 
OUTPUT_PATH = 'processed_data_v3'
CROP_SIZE = 64

def parse_xml_annotations(xml_path):
    nodules = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {'ns': 'http://www.nih.gov'} 
        
        for reading_session in root.findall('ns:readingSession', ns):
            for unblinded_read in reading_session.findall('ns:unblindedReadNodule', ns):
                roi = unblinded_read.find('ns:roi', ns)
                if roi is None:
                    continue
                
                image_uid_elem = roi.find('ns:imageSOP_UID', ns)
                if image_uid_elem is None:
                    continue

                characteristics = unblinded_read.find('ns:characteristics', ns)
                if characteristics is None:
                    continue
                
                malignancy = characteristics.find('ns:malignancy', ns)
                if malignancy is None or malignancy.text is None:
                    continue
                    
                malignancy_score = int(malignancy.text)
                
                edge_maps = roi.findall('ns:edgeMap', ns)
                all_coords = []
                for edge_map in edge_maps:
                    x_elem = edge_map.find('ns:xCoord', ns)
                    y_elem = edge_map.find('ns:yCoord', ns)
                    if x_elem is not None and y_elem is not None:
                        all_coords.append((int(x_elem.text), int(y_elem.text)))
                
                if not all_coords:
                    continue

                center_x = int(np.mean([c[0] for c in all_coords]))
                center_y = int(np.mean([c[1] for c in all_coords]))

                nodules.append({
                    'image_uid': image_uid_elem.text,
                    'center_x': center_x,
                    'center_y': center_y,
                    'malignancy': malignancy_score
                })
    except Exception as e:
        pass
        
    return nodules


def process_patient_all_scans(patient_folder):
    all_slices = {}
    xml_files = []
    
    for root, dirs, files in os.walk(patient_folder):
        for f in files:
            if f.endswith('.xml'):
                xml_files.append(os.path.join(root, f))
            elif f.endswith('.dcm'):
                try:
                    dcm_path = os.path.join(root, f)
                    ds = pydicom.dcmread(dcm_path)
                    if hasattr(ds, 'SOPInstanceUID'):
                        all_slices[ds.SOPInstanceUID] = ds.pixel_array
                except:
                    pass
    
    if not xml_files or not all_slices:
        return []
    
    all_nodules = []
    for xml_path in xml_files:
        all_nodules.extend(parse_xml_annotations(xml_path))
    
    processed_nodules = []
    
    for nodule in all_nodules:
        if nodule['image_uid'] not in all_slices:
            continue
            
        image_slice = all_slices[nodule['image_uid']]
        
        image_slice = np.clip(image_slice, -1000, 400)
        if np.max(image_slice) - np.min(image_slice) == 0:
            continue
        image_slice = (image_slice - np.min(image_slice)) / (np.max(image_slice) - np.min(image_slice))
        image_slice = (image_slice * 255).astype(np.uint8)

        x, y = nodule['center_x'], nodule['center_y']
        half = CROP_SIZE // 2
        
        if (y - half < 0 or y + half > image_slice.shape[0] or 
            x - half < 0 or x + half > image_slice.shape[1]):
            continue
        
        cropped_patch = image_slice[y - half : y + half, x - half : x + half]
        
        if cropped_patch.shape != (CROP_SIZE, CROP_SIZE):
            continue

        label = 'malignant' if nodule['malignancy'] > 3 else 'benign'
        
        processed_nodules.append({'patch': cropped_patch, 'label': label})
        
    return processed_nodules


if __name__ == "__main__":
    os.makedirs(os.path.join(OUTPUT_PATH, 'malignant'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_PATH, 'benign'), exist_ok=True)

    patient_folders = [
        os.path.join(RAW_DATA_PATH, f) 
        for f in os.listdir(RAW_DATA_PATH) 
        if f.startswith('LIDC-IDRI')
    ]
    
    total_nodules = 0
    
    for patient_folder in tqdm(patient_folders, desc="Processing"):
        nodules = process_patient_all_scans(patient_folder)
        patient_id = os.path.basename(patient_folder)
        
        for i, nodule_data in enumerate(nodules):
            filename = f"{patient_id}_nodule_{total_nodules + i}.png"
            save_path = os.path.join(OUTPUT_PATH, nodule_data['label'], filename)
            cv2.imwrite(save_path, nodule_data['patch'])
        
        total_nodules += len(nodules)

    print(f"\nTotal nodules extracted: {total_nodules}")
    print(f"Expected ~400, got {total_nodules/400*100:.1f}%")