from django.contrib.auth.models import User

def check_duplicate_username(newusername):
    chars = ["'", "-", "\"", "_", "."]
    print(newusername)
    for x in chars:
        if x in newusername:
            newusername = newusername.replace(x, "")
    print(newusername)
    inputname = newusername
    inc = 1
    while User.objects.filter(username=newusername).exists():
        if len(inputname) < len(newusername):
            offset = len(newusername) - len(inputname)
            inc = int(newusername[-offset:]) + 1
        newusername = inputname + '{}'.format(inc)
        print(newusername)
    return newusername