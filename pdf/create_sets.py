import random
import os
import shutil

if not os.path.exists('training'):
    os.mkdir("training")
if not os.path.exists('tests'):
    os.mkdir("tests")

for f in os.listdir('.'):
    if f.endswith('.pdf'):
        if random.randrange(5) == 0:
            shutil.copy(f, 'training')
        else:
            shutil.copy(f, 'tests')

        
    

