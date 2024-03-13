# TikTok Direct Message Bot

This script provides a way to automate certain actiivties on TikTok i.e. sending direct messages.
Support for chrome profiles - automatic logging in and manual logging in.

## Dependencies

To use this script, you need to have the following Python packages installed:

    selenium
    pyotp

You can install them using the following command:

    pip3 install selenium pyotp

## Basic usage

Import the TikTok class from the script:
````py
from tiktok_web import Session
````

Create an instance of the TikTok session:

````py
 #To use chrome profiles
session = Session(profile_name="profile_name", debug=False)                                                      

 #To use it to login automatically but dont save session 
session = Session(username="your_username",password="your_password",token="your_2fa_token(optional)", debug=False)   

#To use both chrome profiles to save session and aoutomatic login  
session = Session(profile_name="profile_name",username="your_username",password="your_password",token="your_2fa_token(optional)")

#You dont have to use profiles or automatic login but you would have to login every time by yourself
session = Session()    
````


#
Send a direct message to another user:
```py
session.send_msg(username="recipient_username", msg="Your message here")
````



Get info about specified username
````py
cookies = session.get_user_info(username="")
````

Other functions that are self explanatory
````py
dm_blocker()
dm_cleaner()
video_deleter()
favorite_delete()
liked_delete()
unfollower()
unarchiver()
````

## Notes
If you have any questions or feedback feel free to contact me.

This script is provided for educational purposes only. Automating actions on TikTok may violate their terms of service, and your account may be subject to restrictions or bans. Use this script at your own risk.


