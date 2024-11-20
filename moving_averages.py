import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import pdist, squareform
from scipy import stats

fname = "data/csv/new_Intact_1.csv"

tbl = pd.read_csv(fname)
data = tbl.to_numpy()

# Преобразование данных
data1 = np.transpose(data[:, 1:], (0, 2, 1)).reshape(data.shape[0], -1, 2)

# Инициализация массива расстояний
dist = np.full((data1.shape[0], data1.shape[1] - 1), np.nan)

# Вычисление расстояний
for k in range(len(data1)):
    dist[k, :] = np.diag(squareform(pdist(np.transpose(data1[k, :, :], (1, 2, 0)))), 1)

# Инициализация масок
filt = np.full(dist.shape, np.nan)
mask = np.full(dist.shape, np.nan)
t = np.full(dist.shape, np.nan)

# Применение градиента и создание маски
for n in range(dist.shape[1]):
    gradient = np.gradient(dist[:, n])
    mask[:, n] = np.abs(gradient) < np.percentile(np.abs(gradient), 95)
    t[~mask[:, n], n] = np.where(~mask[:, n])[0]

# Визуализация
plt.plot(dist)
plt.hold(True)  # В matplotlib нет hold, просто добавляйте новые графики
plt.plot(t, filt, 'o')

# Обнуление значений в data1 на основе маски
for n in range(dist.shape[1]):
    data1[np.where(mask[:, n]), n, :] = 0
    if n + 1 < data1.shape[1]:  # Проверка, чтобы избежать выхода за границы
        data1[np.where(mask[:, n]), n + 1, :] = 0

# Восстановление данных в оригинальный массив
data[:, 1:] = np.transpose(data1, (0, 2, 1)).reshape(data.shape[0], data.shape[1] - 1)

# Сохранение данных в новый CSV
tbl.iloc[:data.shape[0], :data.shape[1]] = pd.DataFrame(data)
tbl.to_csv(fname[:-4] + ' filtered.csv', index=False)