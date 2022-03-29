import numpy as np
import pandas as pd
import os
import librosa
import sys
import IPython
import matplotlib
import matplotlib.pyplot as plt
import requests
import torch
import pickle
import torchaudio
from pathlib import Path
from tqdm import tqdm
from sklearn.model_selection import train_test_split

#################
torch.random.manual_seed(0)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

##################
bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
model = bundle.get_model().to(device)

##################
EMOTIONS = {0: 'surprise', 1: 'calm', 2: 'happy', 3: 'sad', 4: 'angry', 5: 'fear',
            6: 'disgust'}  # surprise has been changed from 8 to 0
RAVDESS_PATH = 'data\\ravdess'
TESS_PATH = 'data\\tess'
URDU_PATH = 'data\\urdu'
SAMPLE_RATE = 16000
count_calm = 0
data = pd.DataFrame(columns=['Emotion', 'Gender', 'Path'])

for dirname, _, filenames in os.walk(RAVDESS_PATH):
    for filename in filenames:
        file_path = os.path.join('\\', dirname, filename)
        identifiers = filename.split('.')[0].split('-')

        emotion = (int(identifiers[2]))
        flag_change = False

        if emotion == 2:
            emotion = 1

        if emotion == 8:  # surprise has been changed from 8 to 0
            emotion = 0
            flag_change = True

        if emotion == 1:
            count_calm += 1
            flag_change = True

        if int(identifiers[6]) % 2 == 0:  # actor id. (even = female, odd = male)
            gender = 'female'
        else:
            gender = 'male'

        path_fix = file_path.split('\\')
        file_path = path_fix[1]
        file_path += '/' + path_fix[2]
        file_path += '/' + path_fix[3]
        file_path += '/' + path_fix[4]

        if flag_change:
            data = data.append({"Emotion": emotion,
                                "Gender": gender,
                                "Path": file_path
                                },
                               ignore_index=True
                               )
        else:
            emotion -= 1
            data = data.append({"Emotion": emotion,
                                "Gender": gender,
                                "Path": file_path
                                },
                               ignore_index=True
                               )

for dirname, _, filenames in os.walk(TESS_PATH):
    for filename in filenames:
        file_path = os.path.join('\\', dirname, filename)
        identifiers = filename.split('.')[0].split('_')
        emotion = identifiers[2]

        if emotion == 'angry':
            emotion = 4
        if emotion == 'disgust':
            emotion = 6
        if emotion == 'fear':
            emotion = 5
        if emotion == 'happy':
            emotion = 2
        if emotion == 'neutral':
            emotion = 1
            count_calm += 1
        if emotion == 'ps':
            emotion = 0
        if emotion == 'sad':
            emotion = 3

        if identifiers[0] == 'YAF':  # actor id. (even = female, odd = male)
            gender = 'female'
        else:
            gender = 'male'

        if emotion == 1 and count_calm > 592:
            continue

        path_fix = file_path.split('\\')
        file_path = path_fix[1]
        file_path += '/' + path_fix[2]
        file_path += '/' + path_fix[3]
        file_path += '/' + path_fix[4]

        data = data.append({"Emotion": emotion,
                            "Gender": gender,
                            "Path": file_path
                            },
                           ignore_index=True
                           )


for dirname, _, filenames in os.walk(URDU_PATH):
    for filename in filenames:
        file_path = os.path.join('\\', dirname, filename)
        identifiers = filename.split('.')[0].split('_')
        emotion = dirname[10:]

        if emotion == 'Angry':
            emotion = 4
        if emotion == 'Happy':
            emotion = 2
        if emotion == 'Neutral':
            emotion = 1
        if emotion == 'Sad':
            emotion = 3

        if identifiers[0][1] == 'F':  # actor id. (even = female, odd = male)
            gender = 'female'
        else:
            gender = 'male'

        path_fix = file_path.split('\\')
        file_path = path_fix[1]
        file_path += '/' + path_fix[2]
        file_path += '/' + path_fix[3]
        file_path += '/' + path_fix[4]

        data = data.append({"Emotion": emotion,
                            "Gender": gender,
                            "Path": file_path
                            },
                           ignore_index=True
                           )


# print(data.groupby("Emotion").count()[["Path"]])

##################
def speech_file_to_array_fn(path):
    waveform, sampling_rate = torchaudio.load(filepath=path, num_frames=SAMPLE_RATE * 3)
    waveform = waveform.to(device)

    if (len(waveform[0]) < 48000):
        print(f'less than 3 seconds: {path}')

    return waveform


def normalize_features(features):
    for i in range(len(features[0])):
        mlist = features[0][i]
        features[0][i] = 2 * (mlist - np.max(mlist)) / (np.max(mlist) - np.min(mlist)) + 1


# filehandler = open('data/datasets/dataset_linux.pth', 'rb')
# signals = pickle.load(filehandler)
signals = []

j = 1
total_data = len(data)
with torch.inference_mode():
    for i, file_path in enumerate(data.Path):
        emission, _ = model(speech_file_to_array_fn(file_path))
        features = emission.detach().cpu().numpy()
        normalize_features(features)
        check = 0
        if features.shape[1] != 149:
            print(f'\n{j} is not in shape of 149, current shape: {features.shape[1]}')
            check += 1
        if features.shape[2] != 29:
            print(f'\n{j} is not in shape of 29, current shape: {features.shape[2]}')
            check += 1
        max = np.max(features)
        min = np.min(features)
        if max > 1:
            print(f'\n{j} max is not 1, current max: {max}')
            check += 1
        if min < -1:
            print(f'\n{j} min is not -1, current min: {min}')
            check += 1

        if check == 0:
            row = (file_path, features, data.iloc[i]['Emotion'])
            signals.append(row)
        else:
            total_data -= 1

        j += 1
        percent = (len(signals) / total_data) * 100
        print("\r Processed {}/{} files. ({}%) ".format(len(signals), total_data, int(percent)), end='')

file_pth = open('data/datasets/dataset2.pth', 'wb')
pickle.dump(signals, file_pth)

# 3496

if __name__ == '__main__':
    filehandler = open('data/datasets/dataset2.pth', 'rb')
    check_sig = pickle.load(filehandler)
    new_distribution = []
    counter = [0 for i in range(7)]
    classes = [0, 0, 0]
    for tup in check_sig:
        counter[tup[2]] += 1
        m_class = -1
        if tup[2] == 0 or tup[2] == 2: # POSITIVE( HAPPY, SURPRISED )
            m_class = 0
        if tup[2] == 1: # NEUTRAL( CALM ) USELESS CONDITION ONLY FOR UNDERSTANDING
            m_class = 1
        if tup[2] == 3 or tup[2] == 4 or tup[2] == 5 or tup[2] == 6: # NEGATIVE( SAD, ANGRY, FEAR, DISGUST )
            m_class = 2

        classes[m_class] += 1

        new_distribution.append((tup[0], tup[1], m_class))

    print(f'Before: {counter}, total: {np.sum(counter)}')
    print(f'After: {classes}, total: {np.sum(classes)}')

    file_pth = open('data/datasets/dataset3.pth', 'wb')
    pickle.dump(new_distribution, file_pth)


# OLD: [0: surprise, 1 :calm, 2:happy, 3: sad, 4: angry, 5: fear, 6: disgust]
# NEW: [0: positive, 1: neutral, 2: negative]
# now: [407, 613, 522, 691, 469, 202, 592]
# before: [407, 513, 422, 591, 370, 202, 592]
