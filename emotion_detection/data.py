# Imports
import torch
from torch.utils.data import DataLoader, Dataset
from torchvision import datasets, transforms
import os
import pandas as pd
import numpy as np
from skimage import exposure
from skimage.transform import resize as sk_resize
import warnings
warnings.filterwarnings('ignore', category=UserWarning)


# Define the transforms for the training and validation sets
BATCH_SIZE = 256
DATA_DIR = "../../fer2013/fer2013.csv"


def get_dataloaders(batch_size=BATCH_SIZE, data_dir=DATA_DIR,
                    chunksize=10000, resize=None, to_rgb=True, hist_eq=False, normalize=False):

    to_rgb = None
    chunksize = None
    resize = None
    hist_eq = None

    list_transforms = [transforms.ToTensor()]
    if normalize:
        list_transforms = list_transforms + [transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]
    data_transforms = {
        'Training': transforms.Compose(list_transforms),
        'PublicTest': transforms.Compose(list_transforms)
    }

    # Load the datasets with ImageFolder
    image_datasets = {
        x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x])
        for x in ['Training', 'PublicTest']
    }

    # Using the image datasets and the transforms, define the dataloaders
    dataloaders = {
        x: DataLoader(image_datasets[x], batch_size=batch_size, num_workers=4, shuffle=True)
        for x in ['Training', 'PublicTest']
    }

    return dataloaders


def get_dataloaders_fer48(data_dir, batch_size=BATCH_SIZE, chunksize=10000,
                          resize=None, add_channel_dim=False, to_rgb=True, hist_eq=False, normalize=False):

    """

    :param data_dir:
    :param batch_size:
    :param chunksize:
    :param transform:
    :return:
    """

    class AddChannel(object):
        def __call__(self, im):
            return np.expand_dims(im, 2)

    class HistEq(object):
        def __call__(self, im):
            # res = AddChannel()(exposure.equalize_hist(im))
            return exposure.equalize_hist(im)

    class ToRGB(object):
        def __call__(self, im):
            if len(im.shape) < 3:
                im = np.expand_dims(im, 2)
            return np.repeat(im, 3, axis=2)

    class SkResize(object):
        def __init__(self, size):
            self.size = size

        def __call__(self, im, size=None):
            return sk_resize(im, self.size)

    data_transforms = [transforms.ToTensor()]
    if resize:
        # data_transforms = [transforms.Resize(resize)] + data_transforms
        data_transforms = [SkResize(resize)] + data_transforms
        if hist_eq:
            data_transforms.insert(1, HistEq())
            if to_rgb:
                data_transforms.insert(2, ToRGB())
            elif add_channel_dim:
                data_transforms.insert(2, AddChannel())
        elif to_rgb:
            data_transforms.insert(1, ToRGB())

    elif hist_eq:
        data_transforms = [HistEq()] + data_transforms
        if to_rgb:
            data_transforms.insert(1, ToRGB())
        elif add_channel_dim:
            data_transforms.insert(1, AddChannel())
    elif to_rgb:
        data_transforms = [ToRGB()] + data_transforms
    elif add_channel_dim:
        data_transforms = [AddChannel()] + data_transforms

    if normalize:
        data_transforms = data_transforms + [transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]

    data_transforms = transforms.Compose(data_transforms)

    image_datasets = {
        x: FerDataset48(data_dir, x, chunksize, data_transforms)
        for x in ['Training', 'PublicTest']
    }

    # Using the image datasets and the transforms, define the dataloaders
    dataloaders = {
        x: DataLoader(image_datasets[x], batch_size=batch_size, num_workers=8, shuffle=True)
        for x in ['Training', 'PublicTest']
    }

    return dataloaders


class FerDataset48(Dataset):
    """
    Custom pytorch dataset class implementation to load utk_face images
    """

    def __init__(self, data_dir, flag, chunksize=20000, transform=None):
        """

        :param root_dir:
        :param transform:
        """
        self.data = self._read_csv(data_dir, chunksize, flag)
        self.transform = transform

    def __len__(self):
        """

        :return:
        """
        return self.data.shape[0]

    def __getitem__(self, idx):
        """

        :param idx:
        :return:
        """

        im = np.array([
            int(i) for i in self.data['pixels'].iloc[idx].split(' ')
        ]).reshape((48, 48))

        # lab = np.array(self.data['emotion'].iloc[idx]).reshape((1, 1)).astype(np.uint8)
        lab = np.array(self.data['emotion'].iloc[idx]).astype(np.uint8)

        im, lab = self.transform(im).to(torch.float32), torch.from_numpy(lab).long()  # torch.from_numpy(lab).unsqueeze_(0)
        # print(im.dtype, im.size())
        # print(lab.dtype, lab.size())

        return im, lab

    def _read_csv(self, path_to_csv, chunksize, flag='Training'):
        chunks = pd.read_csv(path_to_csv, sep=',', chunksize=chunksize)
        list_chunks = []
        for chunk in chunks:
            mask = chunk['Usage'] == flag
            list_chunks.append(chunk.loc[mask])
        return pd.concat(list_chunks)

data_loader_lambda = {
    'get_dataloaders_fer48': get_dataloaders_fer48,
    'get_dataloaders': get_dataloaders
}