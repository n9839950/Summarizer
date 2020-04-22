import os
import sys
import logging
import datetime
import torch
from torch.autograd import Variable
from torch.utils.tensorboard import SummaryWriter
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from summarizer.utils import parse_splits_filename
from summarizer.models.vasnet import VASNetModel
from summarizer.models.transformer import TransformerModel
from summarizer.models.DSN import DSNModel
from summarizer.models.baseline import LogisticRegressionModel
from summarizer.models.sumgan import SumGANModel


class HParameters:
    """Hyperparameters configuration class"""
    def __init__(self):
        self.verbose = False
        self.use_cuda = False
        self.cuda_device = 0
        self.max_summary_length = 0.15

        self.l2_req = 0.00001
        self.lr = 0.00005

        self.epochs_max = 300
        self.train_batch_size = 1
        self.test_every_epochs = 2

        # Project root directory
        self.root = ''
        # self.datasets = ['datasets/eccv16_dataset_summe_google_pool5.h5',
        #                 'datasets/eccv16_dataset_tvsum_google_pool5.h5',
        #                 'datasets/eccv16_dataset_ovp_google_pool5.h5',
        #                 'datasets/eccv16_dataset_youtube_google_pool5.h5']
        self.datasets = ['datasets/summarizer_dataset_summe_google_pool5.h5',
                        'datasets/summarizer_dataset_tvsum_google_pool5.h5']

        # Split files to be trained/tested on
        self.splits_files = [
            'splits/tvsum_splits.json',
            'splits/summe_splits.json'
        ]

        # Default model
        self.model_class = LogisticRegressionModel

        # Test mode
        self.test = False
        self.weights_path = None
        self.weights_of_file = None

        # Dict containing extra parameters, possibly model-specific
        self.extra_params = None

    def load_from_args(self, args):
        # Any key from flags
        for key in args:
            val = args[key]
            if val is not None:
                if hasattr(self, key) and isinstance(getattr(self, key), list):
                    val = val.split()
                setattr(self, key, val)

        # Pick model
        if "model" in args:
            self.model_class = {
                "baseline": LogisticRegressionModel,
                "vasnet": VASNetModel,
                "transformer": TransformerModel,
                "DSN": DSNModel,
                "sumgan": SumGANModel
            }.get(args["model"], LogisticRegressionModel)

        # Other dynamic properties
        self._init()

    def _init(self):
        # Experiment name, used as output directory
        log_dir = str(int(datetime.datetime.now().timestamp()))
        log_dir += "_" + self.model_class.__name__
        self.log_path = os.path.join("logs", log_dir)
        self.writer = SummaryWriter(self.log_path)

        # Handle use_cuda flag
        if self.use_cuda == "default":
            self.use_cuda = torch.cuda.is_available()
        elif self.use_cuda == "yes":
            self.use_cuda = True
        else:
            self.use_cuda = False

        # List of splits by filename
        self.dataset_name_of_file = {}
        self.dataset_of_file = {}
        self.splits_of_file = {}
        for splits_file in self.splits_files:
            dataset_name, splits = parse_splits_filename(splits_file)
            self.dataset_name_of_file[splits_file] = dataset_name
            self.dataset_of_file[splits_file] = self.get_dataset_by_name(dataset_name).pop()
            self.splits_of_file[splits_file] = splits

        # Destination for weights and predictions on dataset
        self.weights_path = {}
        self.pred_path = {}
        for splits_file in self.splits_files:
            weights_file = f"{os.path.basename(splits_file)}.pth"
            self.weights_path[splits_file] = os.path.join(self.log_path, weights_file)
            pred_file = f"{os.path.basename(splits_file)}_preds.h5"
            self.pred_path[splits_file] = os.path.join(self.log_path, pred_file)

        # Check if test mode, path for weights is given
        if self.test:
            assert self.weights_path is not None, "No weights path given"
            self.weights_of_file = {}
            for splits_file in self.splits_files:
                splits_file_filename = os.path.basename(splits_file)
                self.weights_of_file[splits_file] = os.path.join(
                    self.weights_path, splits_file_filename + ".pth")
        else:
            # Create log path if does not exist
            os.makedirs(self.log_path, exist_ok=True)

        # Logger
        self.logger = logging.getLogger("summarizer")
        fmt = logging.Formatter("%(asctime)s::%(levelname)s: %(message)s", "%H:%M:%S")
        ch = logging.StreamHandler()
        fh = logging.FileHandler(os.path.join(self.log_path, "train.log"))
        ch.setFormatter(fmt)
        fh.setFormatter(fmt)
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.INFO) # TODO: what default level to use? +add flag to set it

    def get_dataset_by_name(self, dataset_name):
        for d in self.datasets:
            if dataset_name in d:
                return [d]
        return None

    def __str__(self):
        """Nicely lists hyperparameters when object is printed"""
        vars = ["verbose", "use_cuda", "cuda_device",
                "l2_req", "lr", "epochs_max",
                "log_path", "splits_files", "extra_params"]
        info_str = ''
        for i, var in enumerate(vars):
            val = getattr(self, var)
            if isinstance(val, Variable):
                val = val.data.cpu().numpy().tolist()[0]
            info_str += "["+str(i)+"] "+var+": "+str(val)
            info_str += "\n" if i < len(vars)-1 else ""

        return info_str

    def get_full_hps_dict(self):
        """Returns the list of hyperparameters as a flat dict"""
        vars = ["l2_req", "lr", "epochs_max"]

        hps = {}
        for i, var in enumerate(vars):
            val = getattr(self, var)
            if isinstance(val, Variable):
                val = val.data.cpu().numpy().tolist()[0]
            hps[var] = val

        return hps

if __name__ == "__main__":
    # Check default values
    hps = HParameters()
    print(hps)
    # Check update with args works well
    args = {
        'root': 'root_dir',
        'datasets': 'set1,set2,set3',
        'splits': 'split1, split2',
        'new_param_float': 1.23456
    }
    hps.load_from_args(args)
    print(hps)
