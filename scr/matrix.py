import numpy as np

from utilities import to_xy

def check_transform(t):
    try:
        t = np.array(t,dtype=float)
        if t.shape != (3,3) or np.linalg.det(t) == 0: raise
    except:
        raise ValueError(f"{t}不是支持的transform值，支持(3,3)的数组类型且可逆的变换矩阵")
    return t

def _to_xy1(xy):
    xy = to_xy(xy)
    return np.array([[xy[0]],[xy[1]],[1]],dtype=float)
# 根据变换矩阵获取
def get_origin_by_transform(t):
    t = check_transform(t)
    x,y,_ = np.dot(t,np.array([[0],[0],1]))
    return np.array((x,y),dtype=float)
# 获取坐标
def get_xy_by_transform(t,xy):
    xy = _to_xy1(xy)
    t = check_transform(t)
    x,y,_ = np.dot(t,xy)
    return x[0],y[0]
# 获取变换矩阵
def get_transform_by_rad(mat,rad):
    mat = check_transform(mat)
    A = np.array([[np.cos(rad),-np.sin(rad),0],
                  [np.sin(rad),np.cos(rad),0],
                  [0,0,1]])
    return np.dot(mat,A)
def get_transform_by_translate(mat,v):
    mat = check_transform(mat)
    v = to_xy(v)
    A = np.array([[1,0,v[0]],
                  [0,1,v[1]],
                  [0,0,1]])
    return np.dot(mat,A)
def get_transform_by_scale(mat,x,y):
    mat = check_transform(mat)
    x,y = to_xy((x,y))
    A = np.array([[x,0,0],
                  [0,y,0],
                  [0,0,1]])
    return np.dot(mat,A)
def get_transform_by_origin(mat,a,b):
    mat = check_transform(mat)
    mat[0][-1] = a 
    mat[1][-1] = b
    return mat 
def get_transform_by_viewport(mat,start,end,bounds = (1,1)):
    start,end,bounds = map(to_xy,(start,end,bounds))
    mat = check_transform(mat)
    mat = get_transform_by_origin(mat,*start)
    xscale,yscale = (end - start)/bounds
    mat = get_transform_by_scale(mat,xscale,yscale)
    return mat 

if __name__ == '__main__':
    pass