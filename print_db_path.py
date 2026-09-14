import sys
import os
sys.path.insert(0, '/home/kai/projects/cyber-shats')
from app import app
print("DB_PATH is:", app.config['DB_PATH'])
