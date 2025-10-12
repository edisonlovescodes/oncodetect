# preprocess_data.py (Version 2 - More Robust)

import os
import pydicom
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from tqdm import tqdm

# --- CONFIGURATION ---
RAW_DATA_PATH = 'raw_data/LIDC-IDRI' 
OUTPUT_PATH = 'processed_data'
CROP_SIZE = 64
# ---------------------

def parse_xml_annotations_v2(xml_path):
    nodules = []
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'ns': 'http://www.nih.gov'} 
    
    # We need to find the unique ID for each image slice (SOPInstanceUID)
    # and match it to the nodule annotation.
    for reading_session in root.findall('ns:readingSession', ns):
        for unblinded_read in reading_session.findall('ns:unblindedReadNodule', ns):
            nodule_id = unblinded_read.find('ns:noduleID', ns).text
            
            # *** KEY CHANGE #1: We now get the SOPInstanceUID for the slice ***
            roi = unblinded_read.find('ns:roi', ns)
            if roi is None: continue
            image_uid = roi.find('ns:imageSOP_UID', ns).text 

            characteristics = unblinded_read.find('ns:characteristics', ns)
            if characteristics is None: continue
            malignancy = characteristics.find('ns:malignancy', ns)
            if malignancy is None: continue
            malignancy_score = int(malignancy.text)
            
            edge_maps = roi.findall('ns:edgeMap', ns)
            all_coords = []
            for edge_map in edge_maps:
                x = int(edge_map.find('ns:xCoord', ns).text)
                y = int(edge_map.find('ns:yCoord', ns).text)
                all_coords.append((x, y))
            
            if not all_coords: continue

            center_x = int(np.mean([c[0] for c in all_coords]))
            center_y = int(np.mean([c[1] for c in all_coords]))

            nodules.append({
                'nodule_id': nodule_id,
                'image_uid': image_uid,  # We store the slice UID
                'center_x': center_x,
                'center_y': center_y,
                'malignancy': malignancy_score
            })
    return nodules

def process_scan_v2(scan_path):
    try:
        xml_files = [f for f in os.listdir(scan_path) if f.endswith('.xml')]
        if not xml_files: return []

        xml_path = os.path.join(scan_path, xml_files[0])
        nodule_annotations = parse_xml_annotations_v2(xml_path)
        
        # *** KEY CHANGE #2: Create a dictionary mapping slice UID to its image data ***
        dicom_files = [f for f in os.listdir(scan_path) if f.endswith('.dcm')]
        slices = {}
        for dcm_file in dicom_files:
            dcm_path = os.path.join(scan_path, dcm_file)
            ds = pydicom.dcmread(dcm_path)
            slices[ds.SOPInstanceUID] = ds.pixel_array

        processed_nodules = []
        for nodule in nodule_annotations:
            # *** KEY CHANGE #3: Find the image slice using its UID, not Z-position ***
            if nodule['image_uid'] in slices:
                image_slice = slices[nodule['image_uid']]
                
                # Normalize and crop the image (same as before)
                image_slice = np.clip(image_slice, -1000, 400)
                if np.max(image_slice) - np.min(image_slice) == 0: continue # Avoid division by zero
                image_slice = (image_slice - np.min(image_slice)) / (np.max(image_slice) - np.min(image_slice))
                image_slice = (image_slice * 255).astype(np.uint8)

                x, y = nodule['center_x'], nodule['center_y']
                half = CROP_SIZE // 2
                cropped_patch = image_slice[y - half : y + half, x - half : x + half]
                
                if cropped_patch.shape != (CROP_SIZE, CROP_SIZE): continue

                label = 'malignant' if nodule['malignancy'] > 3 else 'benign'
                
                processed_nodules.append({'patch': cropped_patch, 'label': label})
                
        return processed_nodules
    except Exception as e:
        print(f"  !! Error processing {scan_path}: {e}")
        return []

# --- Main script execution ---
if __name__ == "__main__":
    os.makedirs(os.path.join(OUTPUT_PATH, 'malignant'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_PATH, 'benign'), exist_ok=True)

    patient_folders = [os.path.join(RAW_DATA_PATH, f) for f in os.listdir(RAW_DATA_PATH) if f.startswith('LIDC-IDRI')]
    
    total_nodules_extracted = 0
    for patient_folder in tqdm(patient_folders, desc="Processing Patients"):
        for root, dirs, files in os.walk(patient_folder):
            if any(f.endswith('.dcm') for f in files):
                nodules_from_scan = process_scan_v2(root)
                patient_id = os.path.basename(patient_folder)
                for i, nodule_data in enumerate(nodules_from_scan):
                    patch = nodule_data['patch']
                    label = nodule_data['label']
                    filename = f"{patient_id}_nodule_{total_nodules_extracted}_{i}.png"
                    save_path = os.path.join(OUTPUT_PATH, label, filename)
                    cv2.imwrite(save_path, patch)
                total_nodules_extracted += len(nodules_from_scan)
                break 

    print(f"\nProcessing complete!")
    print(f"Total nodules extracted: {total_nodules_extracted}")
    print(f"Data saved in '{OUTPUT_PATH}'")