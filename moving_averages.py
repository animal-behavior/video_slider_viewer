import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import pdist, squareform
from scipy.stats import zscore

fname = "data/csv/new_Intact_1.csv"

tbl = pd.read_csv(fname)
data = tbl.to_numpy()

# Преобразование данных (Количество кадровб, количество точек, количество координат)
data1 = np.reshape(data[:, 1:], (data.shape[0], 2, -1))
data1 = np.transpose(data1, (0, 2, 1))

# Инициализация массива расстояний
dist = np.full((data1.shape[0], data1.shape[1] - 1), np.nan)

data1 = np.transpose(data1[:, :, :], (1, 2, 0))

# Вычисление расстояний
for k in range(len(data1)):
    dist[k, :] = np.diag(squareform(pdist(data1[k,:,:])), 1)

# Инициализация масок
filt = np.full(dist.shape, np.nan)
mask = np.full(dist.shape, np.nan)
t = np.full(dist.shape, np.nan)

# Применение градиента и создание маски
for n in range(dist.shape[1]):
    mask[:, n] = np.abs(zscore(np.gradient(dist[:, n]))) < 2  # Using z-score for outlier detection
    #t[~mask[:, n], n] = np.where(~mask[:, n])[0]

# Визуализация
plt.plot(dist)
plt.plot(t, filt, 'o')
print(dist.shape[1])
# Обнуление значений в data1 на основе маски
for n in range(dist.shape[1]):
    data1[np.where(mask[:, n]), 0, :] = 0
    data1[np.where(mask[:, n]), 1, :] = 0

# Восстановление данных в оригинальный массив
data[:, 1:] = np.transpose(data1, (0, 2, 1)).reshape(data.shape[0], data.shape[1] - 1)

# Сохранение данных в новый CSV
tbl.iloc[:data.shape[0], :data.shape[1]] = pd.DataFrame(data)
tbl.to_csv(fname[:-4] + ' filtered.csv', index=False)
