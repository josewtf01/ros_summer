#!/usr/bin/env python
import rospy
from std_msgs.msg import String
from std_msgs.msg import Int16
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np;
import matplotlib.pyplot as plt
import operator
car_angle = 90
Steering = rospy.Publisher('/manual_control/steering', Int16, queue_size=1)


speed_value = -100
Speed = rospy.Publisher('/manual_control/speed', Int16, queue_size=1)

Control_Start_Stop = rospy.Publisher("/manual_control/stop_start", Int16, queue_size=1)


def callback(data):
    global car_angle, Steering
    global speed_value, Speed
    global Control_Start_Stop
    #rospy.loginfo(rospy.get_caller_id(), data.data)
    cv_image = CvBridge().imgmsg_to_cv2(data, desired_encoding="bgr8")
    im_in = cv2.cvtColor(cv_image, cv2.COLOR_RGB2GRAY)
    im_inverted = cv2.bitwise_not(im_in)
    #cv2.imshow("inverted",im_inverted)
    #cv2.waitKey(0)
    speed_value = -100


    # cropping image
    #third_x = int(im_in)
    third_y = int(im_in.shape[0]*0.6)
    #print "height cropped = ", third_y, "\n"
    width = int(im_in.shape[1])
    #print "width image = ", width, "\n"
    height = int(im_in.shape[0])
    cropped_image = im_in[third_y:height,0:width]
    cropped_image_2 = cv_image[third_y:height,0:width]
    cropped_image_3 = im_inverted[third_y:height,0:width]
    #cv2.imshow("cropped image color ",cropped_image)
    #cv2.imshow("cropped Image gray ",cropped_image_2)
    #cv2.waitKey(0)

    # Gaussian Blur

    blurred_image_1 = cv2.GaussianBlur(cropped_image_3,(15,15),0)
    #cv2.imshow("GaussianBlur",blurred_image_1)
    #cv2.waitKey(0)

    #threshold

    th, im_th = cv2.threshold(blurred_image_1, 160, 255, cv2.THRESH_BINARY)
    #th, im_th = cv2.threshold(blurred_image_1, 200, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    cv2.imshow("Thresholded Image", im_th)
    cv2.waitKey(1)

    #Morphological transformantion
    # closing

    kernel = np.ones((9,9),np.uint8)
    closing = cv2.morphologyEx(im_th, cv2.MORPH_CLOSE, kernel, iterations = 1)
    #cv2.imshow("closing",closing)
    #cv2.waitKey(0)


    # find contours

    im2, contours, hierarchy = cv2.findContours(closing,cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE)
    #for x in contours[0]:
    #    print(x)

    #ordered contours

    ordered_contours = sorted(contours,key = cv2.contourArea, reverse = True)
    #cv2.drawContours(cropped_image, ordered_contours, -1, (0,255,0), 3)
    #cv2.imshow("contours",cropped_image)
    #cv2.waitKey(0)

    cx_array = []
    cy_array = []
    for x in ordered_contours:
        #print(cv2.contourArea(x))
        if cv2.contourArea(x) > 110:
            # print area
            #print(cv2.contourArea(x))
            M = cv2.moments(x)
            cv2.drawContours(cropped_image_2, x, -1, (0,0,255), 3)
            #x,y,w,h = cv2.boundingRect(x)
            #cv2.rectangle(cropped_image,(x,y),(x+w,y+h),(0,255,0),2)
            cx = int(M['m10']/M['m00'])
            cx_array.append(cx)
            cy = int(M['m01']/M['m00'])
            cy_array.append(cy)
            cv2.circle(cropped_image_2,(cx,cy),10,(0,255,0),3)
            #cv2.imshow("contours",cropped_image_2)
            #cv2.waitKey(0)

    # arrays of centroids xs and ys values

    cx_array_sorted = sorted(cx_array,reverse=True)
    #print "cx_sorted = ", cx_array_sorted, "\n"
    #print "cx = ", cx_array, "\n"
    #print "cy = ", cy_array, "\n"

    #ploting centroids of the blobs

    cy_array_invert = [-x for x in cy_array]
    #plt.plot(cx_array,cy_array_invert,"bo")
    #plt.show()


    list_centroids = {}
    for x in range(len(cx_array)):
        list_centroids[cx_array[x]] = cy_array[x]
    #print "list centroids = ", list_centroids, "\n"
    list_centroids_sorted = sorted(list_centroids.items(), key=operator.itemgetter(0),reverse=True)

    #sorting centroids

    #print("list centroids sorted = ", list_centroids_sorted, "\n")

    # preparing centroids for linear regresion

    x = []
    y = []
    for i in list_centroids_sorted:
        x.append(i[0])
        y.append(i[1])
    #print("x centroids = ", x, "\n")
    #print("y centrois = ", y, "\n" )

    # exclude most right centroid

    x = x[1:]
    y = y[1:]
    #print "x line centroids", x, "\n"
    #print "y line centroids", y, "\n"

    # linear regresion procedure

    x = np.array(x, dtype=np.float64)
    y = np.array(y, dtype=np.float64)

    n_elements = len(x)
    x_sum = sum(x)
    x2_sum = sum(x**2)
    y_sum = sum(y)
    xy_sum = sum(x*y)
    try:
        slope = ((n_elements*xy_sum)-(x_sum*y_sum))/((n_elements*x2_sum)-(x_sum**2))
        b = (y_sum/n_elements)-slope*(x_sum/n_elements)
    except:
        speed_value = 0
        Speed.publish(Int16(speed_value))
        return
    #b = (y_sum/n_elements)-slope*(x_sum/n_elements)
    #print "y = %s*x + %s" %(slope,b), "\n"

    x_test = [cx_array_sorted[-1],cx_array_sorted[-1]+((cx_array_sorted[0]-cx_array_sorted[-1])/2)]
    x_test = np.array(x_test, dtype=np.float64)

    y_calculated = slope*x_test + b
    #plt.plot(x_test,-1*y_calculated)
    #plt.savefig("grafica.png")


    #line from linear regresion
    try:
        cv2.line(cropped_image_2,
        (int(x_test[0]),int(y_calculated[0])),
        (int(x_test[1]),int(y_calculated[1])),
        (255,0,0),
        thickness=4)
    except:
        speed_value = 0
        Speed.publish(Int16(speed_value))
        return
    #cv2.imshow("lines",cropped_image_2)
    #cv2.waitKey(0)

    # line for center
    '''
    cv2.line(cropped_image_2,
    (0,cropped_image_2.shape[0]/2),
    (width,cropped_image_2.shape[0]/2),
    (255,120,0),
    thickness=4)'''

    cv2.line(cropped_image_2,
    (0,cropped_image_2.shape[0]/2),
    (width,cropped_image_2.shape[0]/2),
    (255,120,0),
    thickness=4)
    #cv2.imshow("lines",cropped_image_2)
    #cv2.waitKey(0)


    #y_calculated_mean = third_y/2
    y_calculated_mean = list_centroids_sorted[0][1]
    #y_calculated_mean = third_y
    try:
        x_calculate = (y_calculated_mean-b)/slope
    except:
        speed_value = 0
        Speed.publish(Int16(speed_value))
        return
    x_calculate = int(x_calculate)
    #print " x_calculate = ", x_calculate, "\n"
    #print "y calculated mean = ", y_calculated_mean, "\n"

    x_center_car = int(list_centroids_sorted[0][0])+x_calculate
    x_center_car = int(x_center_car/2)
    y_center_car = int(list_centroids_sorted[0][1]+y_calculated_mean)
    y_center_car = int(y_center_car/2)
    #print "x center car = ", x_center_car, "\n"
    #print "y center car = ", y_center_car, "\n"
    cv2.circle(cropped_image_2,(x_center_car,cropped_image_2.shape[0]/2),12,(0,255,189),3)

    # line for angle
    cv2.line(cropped_image_2,
    (int(width/2),cropped_image_2.shape[0]),
    (x_center_car,cropped_image_2.shape[0]/2),
    (0,120,255),
    thickness=4)

    cv2.line(cropped_image_2,
    (int(width/2),cropped_image_2.shape[0]),
    (int(width/2),cropped_image_2.shape[0]/2),
    (30,155,120),
    thickness=4)


    cv2.circle(cropped_image_2,(int(width/2),cropped_image_2.shape[0]),12,(0,255,189),3)
    a = x_center_car-int(width/2)
    if a > 0 :
        #b = abs(y_center_car-third_y/2)
        b = abs(cropped_image_2.shape[0]-cropped_image_2.shape[0]/2)
        c = ((a**2)+(b**2))**(0.5)
        angle = np.arcsin(a/c)
        angle = angle * 180
        angle = angle / 3.1416
        # car_angle = (90+angle)
        car_angle = ((angle * 29.35)/4.8)
        car_angle *= 0.2
        car_angle = 90+car_angle
        if car_angle > 180:
            car_angle = 90
        print "angulo +  = ", car_angle
        Steering.publish(Int16(car_angle))
        speed_value = -100
        Speed.publish(Int16(speed_value))
    else:
        a = abs(a)
        #b = abs(y_center_car-third_y/2)
        b = abs(cropped_image_2.shape[0]-cropped_image_2.shape[0]/2)
        c = ((a**2)+(b**2))**(0.5)
        angle = np.arcsin(a/c)
        angle = angle * 180
        angle = angle / 3.1416
        #car_angle = (90-angle)
        car_angle = ((angle * 29.35)/4.8)
        car_angle *= 0.2
        car_angle = 90-car_angle
        if car_angle < 0 :
            car_angle = 90
        print "angulo - = ", car_angle
        Steering.publish(Int16(car_angle))
        speed_value = -100
        Speed.publish(Int16(speed_value))
    # final image with blobs and centroids
    #Speed.publish(Int16(speed_value))
    cv2.imshow("lines",cropped_image_2)
    cv2.waitKey(1)
    #rospy.loginfo(data)


def listener():
    global car_angle, Steering
    global speed_value, Speed
    global Control_Start_Stop
    rospy.init_node('listener', anonymous=True)
    rospy.Subscriber('Image', Image, callback)
    Steering.publish(Int16(car_angle))
    #Control_Start_Stop.publish(Int16(0))
    #speed_value = -150
    Speed.publish(Int16(speed_value))
    try:
        rospy.spin()
    except KeyboardInterrupt:
        speed_value = 0
        Speed.publish(Int16(speed_value))
        print "Shutting down ROS Image feature detector module"
        cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        listener()
    except rospy.ROSInterruptException:
        pass
