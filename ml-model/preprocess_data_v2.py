# preprocess_data_v2.py - Improved with SOPInstanceUID matching

import os
import pydicom
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from tqdm import tqdm

# --- CONFIGURATION ---
RAW_DATA_PATH = 'raw_data/LIDC-IDRI' 
OUTPUT_PATH = 'processed_data_v2'
CROP_SIZE = 64
# ---------------------

def parse_xml_annotations_v2(xml_path):
    """
    Parses the LIDC XML file using SOPInstanceUID for more reliable matching.
    """
    nodules = []
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'ns': 'http://www.nih.gov'} 
    
    for reading_session in root.findall('ns:readingSession', ns):
        for unblinded_read in reading_session.findall('ns:unblindedReadNodule', ns):
            nodule_id = unblinded_read.find('ns:noduleID', ns)
            if nodule_id is None:
                continue
            nodule_id = nodule_id.text
            
            roi = unblinded_read.find('ns:roi', ns)
            if roi is None:
                continue
            
            # Use SOPInstanceUID instead of ImagePositionPatient
            image_uid_elem = roi.find('ns:imageSOP_UID', ns)
            if image_uid_elem is None:
                continue
            image_uid = image_uid_elem.text

            characteristics = unblinded_read.find('ns:characteristics', ns)
            if characteristics is None:
                continue
            
            malignancy = characteristics.find('ns:malignancy', ns)
            if malignancy is None or malignancy.text is None:
                continue
                
            malignancy_score = int(malignancy.text)
            
            # Get nodule boundary coordinates
            edge_maps = roi.findall('ns:edgeMap', ns)
            all_coords = []
            for edge_map in edge_maps:
                x_elem = edge_map.find('ns:xCoord', ns)
                y_elem = edge_map.find('ns:yCoord', ns)
                if x_elem is not None and y_elem is not None:
                    x = int(x_elem.text)
                    y = int(y_elem.text)
                    all_coords.append((x, y))
            
            if not all_coords:
                continue

            # Calculate center of nodule
            center_x = int(np.mean([c[0] for c in all_coords]))
            center_y = int(np.mean([c[1] for c in all_coords]))

            nodules.append({
                'nodule_id': nodule_id,
                'image_uid': image_uid,  # Using UID instead of z-position
                'center_x': center_x,
                'center_y': center_y,
                'malignancy': malignancy_score
            })
            
    return nodules


def process_scan_v2(scan_path):
    """
    Processes a scan using SOPInstanceUID matching.
    """
    try:
        # Find XML file
        xml_files = [f for f in os.listdir(scan_path) if f.endswith('.xml')]
        if not xml_files:
            return []

        xml_path = os.path.join(scan_path, xml_files[0])
        nodule_annotations = parse_xml_annotations_v2(xml_path)
        
        if not nodule_annotations:
            return []
        
        # Build dictionary mapping SOPInstanceUID to pixel data
        dicom_files = [f for f in os.listdir(scan_path) if f.endswith('.dcm')]
        slices = {}
        
        for dcm_file in dicom_files:
            dcm_path = os.path.join(scan_path, dcm_file)
            try:
                ds = pydicom.dcmread(dcm_path)
                if hasattr(ds, 'SOPInstanceUID'):
                    slices[ds.SOPInstanceUID] = ds.pixel_array
            except Exception:
                continue

        processed_nodules = []
        
        for nodule in nodule_annotations:
            # Match by UID instead of z-position
            if nodule['image_uid'] not in slices:
                continue
                
            image_slice = slices[nodule['image_uid']]
            
            # Normalize pixel values
            image_slice = np.clip(image_slice, -1000, 400)
            
            # Avoid division by zero
            if np.max(image_slice) - np.min(image_slice) == 0:
                continue
                
            image_slice = (image_slice - np.min(image_slice)) / (np.max(image_slice) - np.min(image_slice))
            image_slice = (image_slice * 255).astype(np.uint8)

            # Crop around nodule center
            x, y = nodule['center_x'], nodule['center_y']
            half = CROP_SIZE // 2
            
            # Check bounds
            if y - half < 0 or y + half > image_slice.shape[0]:
                continue
            if x - half < 0 or x + half > image_slice.shape[1]:
                continue
            
            cropped_patch = image_slice[y - half : y + half, x - half : x + half]
            
            if cropped_patch.shape != (CROP_SIZE, CROP_SIZE):
                continue

            # Label based on malignancy score (>3 = malignant)
            label = 'malignant' if nodule['malignancy'] > 3 else 'benign'
            
            processed_nodules.append({
                'patch': cropped_patch,
                'label': label
            })
            
        return processed_nodules
        
    except Exception as e:
        print(f"  !! Error processing {scan_path}: {e}")
        return []


# --- Main execution ---
if __name__ == "__main__":
    # Create output directories
    os.makedirs(os.path.join(OUTPUT_PATH, 'malignant'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_PATH, 'benign'), exist_ok=True)

    patient_folders = [
        os.path.join(RAW_DATA_PATH, f) 
        for f in os.listdir(RAW_DATA_PATH) 
        if f.startswith('LIDC-IDRI')
    ]
    
    total_nodules = 0
    
    for patient_folder in tqdm(patient_folders, desc="Processing Patients (v2)"):
        for root, dirs, files in os.walk(patient_folder):
            if any(f.endswith('.dcm') for f in files):
                nodules_from_scan = process_scan_v2(root)
                
                patient_id = os.path.basename(patient_folder)
                
                for i, nodule_data in enumerate(nodules_from_scan):
                    patch = nodule_data['patch']
                    label = nodule_data['label']
                    
                    filename = f"{patient_id}_nodule_{total_nodules}_{i}.png"
                    save_path = os.path.join(OUTPUT_PATH, label, filename)
                    
                    cv2.imwrite(save_path, patch)
                
                total_nodules += len(nodules_from_scan)
                break  # Only process first scan folder per patient

    print(f"\nProcessing complete!")
    print(f"Total nodules extracted: {total_nodules}")
    print(f"Data saved in '{OUTPUT_PATH}'")
    
    # Show comparison with v1
    if os.path.exists('processed_data'):
        v1_count = len([f for f in os.listdir('processed_data/malignant') if f.endswith('.png')]) + \
                   len([f for f in os.listdir('processed_data/benign') if f.endswith('.png')])
        print(f"\nComparison:")
        print(f"  V1 extracted: {v1_count} nodules")
        print(f"  V2 extracted: {total_nodules} nodules")
        print(f"  Improvement: +{total_nodules - v1_count} nodules ({((total_nodules/v1_count - 1) * 100):.1f}% increase)")
