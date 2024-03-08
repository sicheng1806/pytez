import numpy as np

from argument import standardize_transform,standardize_xy

def to_xy1(xy):
    xy = standardize_xy(xy)
    return np.array([[xy[0]],[xy[1]],[1]],dtype=float)

def get_origin_by_transform(t):
    t = standardize_transform(t)
    x,y,_ = np.dot(t,np.array([[0],[0],1]))

def get_transformed_xy(t,xy):
    xy = to_xy1(xy)
    t = standardize_transform(t)
    x,y,_ = np.dot(t,xy)
    return x[0],y[0]


if __name__ == '__main__':
    pass