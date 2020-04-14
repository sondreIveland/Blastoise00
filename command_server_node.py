#!/usr/bin/env python
"""
    command_server_node.py

    A ROS node that sends commands based on the current state of the 
    USAR problem. 

    Listens to the start and stop commands on the cmd/ topic. These can be sent with:
    rostopic pub -1 /cmd std_msgs/String -- 'start'
    rostopic pub -1 /cmd std_msgs/String -- 'stop'

    The server starts the search for the beacons when getting 'start' 
    and searches until the map is fully explored or all beacons is found.
    It then returns back to the original starting point. 
    If it get 'stop' does the robot stop and restarts the same task it was doing when 'start' is sent.  

    Subscribed: cmd/
    Publishes: state/, beacons_left/, returning_done/, move_base/status

    Created: 2020/02/04
    Author: Brendan Halloran 
    Changed by: Sondre
"""

import rospy

from commands import Commands, RobotState
from std_msgs.msg import String, Int16, Bool
from std_srvs.srv import SetBool
from actionlib_msgs.msg import GoalStatusArray,  GoalStatus
  

class command_server_node:
    def __init__(self):
        self.state = RobotState.WAITING_TO_START
        self.previusState= RobotState.WAITING_TO_START
        self.subscriber_command = rospy.Subscriber('cmd/', String, self.callback_command)
        self.publisher_state = rospy.Publisher('state/', String, queue_size=1)
        self.subscriber_beacons = rospy.Subscriber('beacons_left/',Int16,self.callback_beacons)
        self.subscriber_returning = rospy.Subscriber('returning_done/',Bool, self.callback_returning)
        self.subscriber_movebase_status =rospy.Subscriber('move_base/status',GoalStatusArray,self.callback_goalstatus)
        # Publish the current state at 10Hz to make sure other nodes get the correct info
        r = rospy.Rate(10)
        while not rospy.is_shutdown():
            self.loop()
            r.sleep()

    # Run at 10Hz
    def loop(self):
        state_msg = String()
        state_msg.data = self.state.value
        self.publisher_state.publish(state_msg)

    # Function that detects when the robot is finished with exploring 
    def callback_goalstatus(self, data):
        statusText = data.status_list[0].text
        if data.status_list[0].status == 2 and len(statusText):
            self.state=RobotState.RETURNING
            self.previusState=RobotState.RETURNING
            print "robot is returning maze is finished explored"
            
     
            
    def callback_beacons(self,beaconsLeft):
        if beaconsLeft.data == 0 and self.state == RobotState.EXPLORING:
            self.state = RobotState.RETURNING
            self.previusState=RobotState.RETURNING
            print "beacons = 0 robot is returning"

    # sends true if the robot is returned
    def callback_returning(self,data):
        if data.data == True and self.state == RobotState.RETURNING: 
            self.state = RobotState.DONE
            self.previusState = RobotState.DONE
            print "robot is returned"


            
    #function that controls the robot. with start or stop command
    def callback_command(self, data):
        command = Commands(data.data)
     
        #start exploring the maze if not all beacons is found
        if command is Commands.START and self.previusState != RobotState.RETURNING:
            self.state = RobotState.EXPLORING
            print "start exploring "
            #wait to see if there is a service for exploration
            rospy.wait_for_service('/explore/explore_service')
            try:
                #send start to the exploration class 
                startFunction = rospy.ServiceProxy('/explore/explore_service',SetBool)
                startFunction(True)
            except rospy.ServiceException, e:
                print "Service call failed: %s" %e
        # start the robot and make it return if the maze is explored
        elif command is Commands.START and self.previusState == RobotState.RETURNING:
            self.state = RobotState.RETURNING
        #stop the robot     
        elif command is Commands.STOP:
            self.state = RobotState.PAUSED
            rospy.wait_for_service('/explore/explore_service')
            try:
                startFunction = rospy.ServiceProxy('/explore/explore_service',SetBool)
                startFunction(False)
            except rospy.ServiceException, e:
                print "Service call failed: %s" %e
    






if __name__ == '__main__':
    print "Starting ROS Command Server module"
    rospy.init_node('command_server_node', anonymous=True)
    cs = command_server_node()
    try:
        rospy.spin()
    except KeyboardInterrupt:
        print "Shutting down ROS Command Server module"