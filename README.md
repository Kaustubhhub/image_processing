sudo systemctl enable --now firewalld && sudo firewall-cmd --permanent --add-port={5000,5001,5002,6001,6002,6003,6004}/tcp && sudo firewall-cmd --reload
