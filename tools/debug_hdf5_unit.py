from app.services.importers.hdf5_importer import Hdf5Importer
import numpy as np
from pathlib import Path
h=Hdf5Importer()
wave=np.linspace(400,700,50)
print('median',np.median(wave))
res=h._import_generic(wave, np.random.normal(1.0,0.1,50), Path('dummy'))
print('x_unit',res.x_unit)
