# preprocess_data_v3.py - Processes ALL scan series per patient

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
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'ns': 'http://www.nih.gov'} 
    
    for reading_session in root.findall('ns:readingSession', ns):
        for unblinded_read in reading_session.findall('ns:unblindedReadNodule', ns):
            nodule_id = unblinded_read.find('ns:noduleID', ns)
            if nodule_id is None:
                continue
                
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

            center_x

