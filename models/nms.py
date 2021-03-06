# 3D IoU caculate code for 3D object detection 
# Kent 2018/12

import numpy as np
import torch
from scipy.spatial import ConvexHull
from numpy import *
import matplotlib
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
import matplotlib.pyplot as plt

def polygon_clip(subjectPolygon, clipPolygon):
   """ Clip a polygon with another polygon.
   Ref: https://rosettacode.org/wiki/Sutherland-Hodgman_polygon_clipping#Python
   Args:
     subjectPolygon: a list of (x,y) 2d points, any polygon.
     clipPolygon: a list of (x,y) 2d points, has to be *convex*
   Note:
     **points have to be counter-clockwise ordered**
   Return:
     a list of (x,y) vertex point for the intersection polygon.
   """
   def inside(p):
      return(cp2[0]-cp1[0])*(p[1]-cp1[1]) > (cp2[1]-cp1[1])*(p[0]-cp1[0])
 
   def computeIntersection():
      dc = [ cp1[0] - cp2[0], cp1[1] - cp2[1] ]
      dp = [ s[0] - e[0], s[1] - e[1] ]
      n1 = cp1[0] * cp2[1] - cp1[1] * cp2[0]
      n2 = s[0] * e[1] - s[1] * e[0] 
      n3 = 1.0 / (dc[0] * dp[1] - dc[1] * dp[0])
      return [(n1*dp[0] - n2*dc[0]) * n3, (n1*dp[1] - n2*dc[1]) * n3]
 
   outputList = subjectPolygon
   cp1 = clipPolygon[-1]
 
   for clipVertex in clipPolygon:
      cp2 = clipVertex
      inputList = outputList
      outputList = []
      s = inputList[-1]
 
      for subjectVertex in inputList:
         e = subjectVertex
         if inside(e):
            if not inside(s):
               outputList.append(computeIntersection())
            outputList.append(e)
         elif inside(s):
            outputList.append(computeIntersection())
         s = e
      cp1 = cp2
      if len(outputList) == 0:
          return None
   return(outputList)

def poly_area(x,y):
    """ Ref: http://stackoverflow.com/questions/24467972/calculate-area-of-polygon-given-x-y-coordinates """
    return 0.5*np.abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))

def convex_hull_intersection(p1, p2):
    """ Compute area of two convex hull's intersection area.
        p1,p2 are a list of (x,y) tuples of hull vertices.
        return a list of (x,y) for the intersection and its volume
    """
    inter_p = polygon_clip(p1,p2)
    if inter_p is not None:
        hull_inter = ConvexHull(inter_p)
        return inter_p, hull_inter.volume
    else:
        return None, 0.0  

def box3d_vol(corners):
    ''' corners: (8,3) no assumption on axis direction '''
    a = np.sqrt(np.sum((corners[0,:] - corners[1,:])**2))
    b = np.sqrt(np.sum((corners[1,:] - corners[2,:])**2))
    c = np.sqrt(np.sum((corners[0,:] - corners[4,:])**2))
    return a*b*c

def is_clockwise(p):
    x = p[:,0]
    y = p[:,1]
    return np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)) > 0

def box3d_iou(corners1, corners2):
    ''' Compute 3D bounding box IoU.
    Input:
        corners1: numpy array (8,3), assume up direction is negative Y
        corners2: numpy array (8,3), assume up direction is negative Y
    Output:
        iou: 3D bounding box IoU
        iou_2d: bird's eye view 2D bounding box IoU
    todo (kent): add more description on corner points' orders.
    '''
    # corner points are in counter clockwise order
    rect1 = [(corners1[i,0], corners1[i,2]) for i in range(3,-1,-1)]
    rect2 = [(corners2[i,0], corners2[i,2]) for i in range(3,-1,-1)] 
    
    area1 = poly_area(np.array(rect1)[:,0], np.array(rect1)[:,1])
    area2 = poly_area(np.array(rect2)[:,0], np.array(rect2)[:,1])
   
    inter, inter_area = convex_hull_intersection(rect1, rect2)
    iou_2d = inter_area/(area1+area2-inter_area)
    ymax = min(corners1[0,1], corners2[0,1])
    ymin = max(corners1[4,1], corners2[4,1])

    inter_vol = inter_area * max(0.0, ymax-ymin)
    
    vol1 = box3d_vol(corners1)
    vol2 = box3d_vol(corners2)
    iou = inter_vol / (vol1 + vol2 - inter_vol)
    return iou, iou_2d

# ----------------------------------
# Helper functions for evaluation
# ----------------------------------

def get_3d_box(box_size, heading_angle, center):
    ''' Calculate 3D bounding box corners from its parameterization.
    Input:
        box_size: tuple of (length,wide,height)
        heading_angle: rad scalar, clockwise from pos x axis
        center: tuple of (x,y,z)
    Output:
        corners_3d: numpy array of shape (8,3) for 3D box cornders
    '''
    def roty(t):
        c = np.cos(t)
        s = np.sin(t)
        return np.array([[c,  0,  s],
                         [0,  1,  0],
                         [-s, 0,  c]])

    R = roty(heading_angle)
    l,w,h = box_size
    x_corners = [l/2,l/2,-l/2,-l/2,l/2,l/2,-l/2,-l/2]
    # y_corners = [h/2,h/2,h/2,h/2,-h/2,-h/2,-h/2,-h/2]
    # z_corners = [w/2,-w/2,-w/2,w/2,w/2,-w/2,-w/2,w/2]
    y_corners = [w/2,w/2,w/2,w/2,-w/2,-w/2,-w/2,-w/2]
    z_corners = [h/2,-h/2,-h/2,h/2,h/2,-h/2,-h/2,h/2]
    #corners_3d = np.dot(R, np.vstack([x_corners,y_corners,z_corners]))
    #print(corners_3d.shape)
    corners_3d = np.vstack([x_corners,y_corners,z_corners])
    corners_3d[0,:] = corners_3d[0,:] + center[0]
    corners_3d[1,:] = corners_3d[1,:] + center[1]
    corners_3d[2,:] = corners_3d[2,:] + center[2]
    corners_3d = np.transpose(corners_3d)
    return corners_3d

def plot_box(points_group):#
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(111, projection='3d')

    for i in range(len(points_group)):
        points = points_group[i]
        #points[:,[1, 2]] = points[:,[2, 1]]
        # P = [[2.06498904e-01 , -6.30755443e-07 ,  1.07477548e-03],
        # [1.61535574e-06 ,  1.18897198e-01 ,  7.85307721e-06],
        # [7.08353661e-02 ,  4.48415767e-06 ,  2.05395893e-01]]
        #Z = np.zeros((8,3))
        #for i in range(8): Z[i,:] = np.dot(points[i,:],P)
        #Z = 10.0*Z
        #Z = points


        #r = [-1,1]

        #X, Y = np.meshgrid(r, r)
        # plot vertices
        ax.scatter3D(points[:, 0], points[:, 1], points[:, 2])

        # list of sides' polygons of figure
        verts = [[points[0],points[1],points[2],points[3]],
        [points[4],points[5],points[6],points[7]], 
        [points[0],points[1],points[5],points[4]], 
        [points[2],points[3],points[7],points[6]], 
        [points[1],points[2],points[6],points[5]],
        [points[4],points[7],points[3],points[0]]]

        # plot sides
        ax.add_collection3d(Poly3DCollection(verts, 
        facecolors='cyan', linewidths=1, edgecolors='r', alpha=.25))


    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # equal axis scale in 3d: https://stackoverflow.com/a/21765085
    pts_stack = np.vstack(points_group)
    max_range = np.array([pts_stack[:, 0].max()-pts_stack[:, 0].min(), 
                        pts_stack[:, 1].max()-pts_stack[:, 1].min(), 
                        pts_stack[:, 2].max()-pts_stack[:, 2].min()]).max() / 2.0

    mid_x = (pts_stack[:, 0].max()+pts_stack[:, 0].min()) * 0.5
    mid_y = (pts_stack[:, 1].max()+pts_stack[:, 1].min()) * 0.5
    mid_z = (pts_stack[:, 2].max()+pts_stack[:, 2].min()) * 0.5

    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)
    #plt.axis('scaled')
    plt.show()

def non_max_suppression_3d(gms, nms_th):
    # x:[p, z, w, h, d]
    matplotlib.use( 'tkagg' )
    pi, mu, sigma = gms

    #x = [pi]
    box = []
    for sigma_ in sigma:
        box_ = 2 * torch.sqrt(5.99 * torch.eig(torch.from_numpy(sigma_))[0][:,0])
        #box_ = 2 * np.sqrt(5.99 * np.linalg.eigvals(sigma_))
        #print(np.linalg.eigvals(sigma_))
        #box_ = 1 * torch.sqrt(torch.eig(torch.from_numpy(sigma_))[0][:,0])
        #print("before flatten: ", box_)
        min_ax = torch.argmin(box_)
        if box_[min_ax] < 0.01:
            box_[min_ax] = 0.1
        #print("after flatten: ", box_)
        box.append(box_.numpy())#
    box = np.asarray(box)
    #print(box)
    x = np.asarray([pi, mu[:, 0], mu[:, 1], mu[:, 2], box[:, 0], box[:, 1], box[:, 2]]).T
    #print(mu[:, 2])

    if len(x) == 0:
        return x

    sorted_gm = np.argsort(-x[:, 0])
    x = x[sorted_gm]
    bboxes = [0]
    sorted_corners = [None for i in range(sorted_gm.shape[0])]
    for i in np.arange(1, len(x)):
        bbox = x[i]

        if sorted_corners[i] is None:
            corners_3d_ground = get_3d_box(bbox[-3:], 0, bbox[1:4])
            sorted_corners[i] = corners_3d_ground
        else: corners_3d_ground = sorted_corners[i]

        # print("candidate: ", bbox[4:])
        flag = 1
        for j in range(len(bboxes)):
            # print("compare: ", i, bboxes[j])
            if sorted_corners[bboxes[j]] is None:
                corners_3d_predict = get_3d_box(x[bboxes[j]][-3:], 0, x[bboxes[j]][1:4])
                sorted_corners[bboxes[j]] = corners_3d_predict
            else: corners_3d_predict = sorted_corners[bboxes[j]]
            #print("corners_3d_predict.z_mean()", corners_3d_predict[:, 1].mean())
            #print("corners_3d_ground.z_mean()", corners_3d_ground[:, 1].mean())
            (IOU_3d,IOU_2d) = box3d_iou(corners_3d_predict,corners_3d_ground)
            #print("IOU_3d = ",IOU_3d)
            #plot_box([corners_3d_ground, corners_3d_predict])

            if IOU_3d > nms_th:
                # print("dropped")
                # print("bboxes: ", bboxes)
                flag = -1
                break
        if flag == 1:
            # print("add to queue")
            bboxes.append(i)
            # print("bboxes: ", bboxes)

    sorted_bboxes = np.asarray(bboxes, np.int32)
    sorted_corners = np.asarray(sorted_corners)
    #print([sorted_corners[bboxes][i, :, 1].mean() for i in range(sorted_corners[bboxes].shape[0])])
    plot_box(sorted_corners[sorted_bboxes])
    true_bboxes = sorted_gm[sorted_bboxes]

    # print("######final bboxe######: ", true_bboxes)
    return pi[true_bboxes], mu[true_bboxes], sigma[true_bboxes]

# 3D-IoU-Python: https://github.com/AlienCat-K/3D-IoU-Python.git
if __name__=='__main__':
    print('------------------')
    # get_3d_box(box_size, heading_angle, center)
    corners_3d_ground  = get_3d_box((1.497255,1.644981, 3.628938), -1.531692, (2.882992 ,1.698800 ,20.785644)) 
    plot_box(corners_3d_ground)
    corners_3d_predict = get_3d_box((1.458242, 1.604773, 3.707947), -1.549553, (2.756923, 1.661275, 20.943280 ))
    (IOU_3d,IOU_2d)=box3d_iou(corners_3d_predict,corners_3d_ground)
    print (IOU_3d,IOU_2d) #3d IoU/ 2d IoU of BEV(bird eye's view)
      