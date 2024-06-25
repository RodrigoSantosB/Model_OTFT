
# Descomente as linhas comentadas caso esteja utilizando no google Colabory
# from google.colab import drive
#drive.mount('/content/gdrive')
import sys
#sys.path.append('/content/gdrive/MyDrive/ICs/beTFT/update models')

# Loading Libraries
import matplotlib.pyplot as plt
import pandas            as pd
import numpy             as np
import itertools
import csv
import os
import re
import ipywidgets as widgets
import plotly.graph_objs as go


from IPython.display import display, HTML
from IPython.display import clear_output
# from google.colab import files
from scipy.optimize import curve_fit

# pip install tabulate;
from tabulate import tabulate
import contextlib
import textwrap
import io
import time
from tqdm import tqdm
np.seterr(divide='ignore', invalid='ignore')
