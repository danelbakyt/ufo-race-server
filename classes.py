from cmu_graphics import *


black  = rgb(31, 31, 31)
white  = rgb(179, 179, 179)
purple = rgb(136, 153, 207)
green  = rgb(141, 199, 111)
yellow = rgb(212, 212, 78)
red    = rgb(206, 67, 69)

class UFO:
    def __init__(self, x, y, r, minY, maxY):
        self.x = x
        self.y = y
        self.r = r
        self.minY = minY
        self.maxY = maxY
        self.score = 100
        self.color = green
        self.collectedStars = set()
        self.isTeleported = False
        self.teleportTimeUp = 0 #after 10 seconds, auto-teleport back
        self.teleportCooldown = 0
        #save home values for teleporting back
        self.homeMinY = minY 
        self.homeMaxY = maxY
        self.isAutoShoot = False
        self.autoShootTimeUp = 0
        self.shootCooldown = 0
        
    def move(self, dy):
        self.y += dy
        if self.y < self.minY + self.r: self.y = self.minY + self.r
        if self.y > self.maxY - self.r: self.y = self.maxY - self.r

    def takeDamage(self, amount):
        self.score -= amount

    def heal(self, amount):
        self.score = min(100, self.score + amount)

class Obstacle:
    def __init__(self, x, y, r, speed, img=None):
        self.x = x
        self.y = y
        self.r = r
        self.speed = speed
        self.img = img
        self.damage = 10
        self.shape = 'circle' #default shape
        
    def update(self):
        self.x -= self.speed
        return self.x > -self.r #return true if obstacle is on screen

class Star(Obstacle):
    def __init__(self, x, y, r, speed, starType):
        #star images will be star0.png, star1.png etc
        img = f'images\star{starType}.png'
        super().__init__(x, y, r, speed, img)
        self.starType = starType
        self.damage = 0
        self.shape = 'star'

#subclass for black holes
class BlackHole(Obstacle):
    def __init__(self, x, y, r, speed):
        super().__init__(x, y, r, speed, img="images/blackhole.png")
        self.damage = 0
        self.shape = 'blackhole'

class Bullet:
    def __init__(self, x, y, r, dx, dy, minY, maxY):
        self.x = x
        self.y = y
        self.r = r
        self.dx = dx
        self.dy = dy
        self.minY = minY
        self.maxY = maxY
        
    def update(self, appWidth):
        self.x += self.dx
        self.y += self.dy
        
        if not (-50 < self.x < appWidth + 50):
            return False
        if not (self.minY <= self.y <= self.maxY):
            return False
        return True #return true if bullet is on screen
