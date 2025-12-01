from cmu_graphics import *
import random
import math
from classes import UFO, Obstacle, Star, BlackHole, Bullet
import websockets
import asyncio
import threading
import json


GAMESERVERURL = "localhost:8765"

async def sendGameData(app, websocket):
    while True:
        #only send data for the player we control
        me = app.p1 if app.myRole == 1 else app.p2
        
        #send dictionaries over JSON
        myData = {
            'role': app.myRole,
            'y': me.y,
            'x': me.x,
            'score': me.score,
            'isTeleported': me.isTeleported,
            'bullets': [{'x': b.x, 'y': b.y} for b in (app.p1Bullets if app.myRole == 1 else app.p2Bullets)]
        }
        
        try:
            #convert to a string and send data
            await websocket.send(json.dumps(myData))
        except:
            print("Error with sending data")
            break
            
        await asyncio.sleep(0.05) # Send 20 times a second


async def receiveUpdates(app):
    uri = f"ws://{GAMESERVERURL}" 
    print(f"Connecting to {uri}...")
    
    async with websockets.connect(uri) as websocket:
        print("Connected!")
        
        #start the sender loop in the background of this async function
        asyncio.create_task(sendGameData(app, websocket))
        
        while True:
            try:
                rawdata = await websocket.recv()
                data = json.loads(rawdata)
                
                #check if this data belongs to another player
                if 'role' in data and data['role'] != app.myRole:
                    updateEnemyState(app, data)
            except Exception as e:
                print(f"Connection error: {e}")
                break


def updateEnemyState(app, data):
    enemy = app.p2 if app.myRole == 1 else app.p1
    
    #sync data of enemy
    enemy.y = data.get('y', enemy.y)
    enemy.x = data.get('x', enemy.x)
    enemy.score = data.get('score', enemy.score)
    enemy.isTeleported = data.get('isTeleported', False)
    
    #sync Bullets (update the list)
    enemyBulletsList = app.p2Bullets if app.myRole == 1 else app.p1Bullets
    enemyBulletsList.clear() # Clear old ones
    
    for bData in data.get('bullets', []):
        # Recreate simple bullets for drawing
        # We assume standard size/speed for visuals
        b = Bullet(bData['x'], bData['y'], app.playerR*0.4, 0, 0, 0, 0)
        enemyBulletsList.append(b)


def runAsyncInThread(app):
    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(receiveUpdates(app))
    t = threading.Thread(target=runner)
    t.start()
    return t

black  = rgb(31, 31, 31)
white  = rgb(179, 179, 179)
purple = rgb(136, 153, 207)
green  = rgb(141, 199, 111)
yellow = rgb(212, 212, 78)
red    = rgb(206, 67, 69)


def onAppStart(app):
    print("Welcome to UFO Race")
    role = input("Enter '1' for Player 1 (Top), '2' for Player 2 (Bottom): ")
    app.myRole = int(role)

    reset(app)
    runAsyncInThread(app)

def reset(app):
    app.paused = False
    app.gameOver = False
    app.winner = None
    
    #horizontal line
    app.split = app.height/2
    
    #player size
    app.playerR = app.height*0.035
    #player position (x doesn't change yet, only y does)
    app.playerX = app.width*0.08
    
    #speeds
    app.bulletSpeed = app.width*0.025
    app.obstacleSpeed = app.width*0.015
    app.dy = app.height*0.02
    
    app.attackRate = 40 #(decrease to make level harder)
    
    #dimensions
    app.barWidth = app.width*0.15
    app.barHeight = app.height*0.03
    app.margin = app.width*0.05
    
    #initialize player objects
    #p1 is top universe (0 to split)
    app.p1 = UFO(app.playerX, app.split/2, app.playerR, 0, app.split)
    
    #p2 is bottom universe (split to height)
    app.p2 = UFO(app.playerX, app.split + (app.split/2), app.playerR, app.split, app.height)
    
    #store objects
    app.p1Bullets = []
    app.p1Obstacles = []
    app.p2Bullets = []
    app.p2Obstacles = []

    app.counter = 0

def onStep(app):
    if app.paused or app.gameOver:
        return
    app.counter += 1
        
    #obstacles are generated not each step, but
    #if random is 0 (so if we decrease attackRate, obstacles will appear more often)
    if random.randint(0, app.attackRate) == 0:
        attackObstacle(app, 1)
    
    # <--- NETWORK CHANGE: ONLY SIMULATE YOUR OWN LOGIC
    me = app.p1 if app.myRole == 1 else app.p2
    myBullets = app.p1Bullets if app.myRole == 1 else app.p2Bullets
    myObstacles = app.p1Obstacles if app.myRole == 1 else app.p2Obstacles
    
    #check for teleportations timer (return to their original screen if time is up)
    if me.isTeleported and app.counter > app.p1.teleportTimeUp:
        app.p1.isTeleported = False
        app.p1.x = app.playerX
        app.p1.minY = app.p1.homeMinY
        app.p1.maxY = app.p1.homeMaxY
        app.p1.y = (app.p1.homeMinY + app.p1.homeMaxY)/2
    
    allObstacles = app.p1Obstacles + app.p2Obstacles
    checkAutoShoot(app, me, myBullets, allObstacles)
        
    #update objects
    updateObjects(app, app.p1Bullets, app.p1Obstacles)
    updateObjects(app, app.p2Bullets, app.p2Obstacles)

    checkTeleportCollision(app, app.p1, app.p2Bullets) 
    checkTeleportCollision(app, app.p2, app.p1Bullets)

    enemyObstacles = app.p2Obstacles if app.myRole == 1 else app.p1Obstacles
    enemyBullets = app.p2Bullets if app.myRole == 1 else app.p1Bullets
    checkCollisions(app, me, myBullets, myObstacles)
    checkCollisions(app, me, myBullets, enemyObstacles)
    checkCollisions(app, me, myBullets, enemyBullets)

    app.split = app.height/2 #to resize WHILE playing, restart (otherwise it'll not work properly)
    
    #gameover check
    if app.p1.score < 0:
        app.gameOver = True
        app.winner = "Player 2"
    elif app.p2.score < 0:
        app.gameOver = True
        app.winner = "Player 1"

#helper to generate obstacles
def attackObstacle(app, playerN):
    r = app.playerR #obstacles same size as player
    x = app.width + r
    
    #random number to decide type of obstacle
    rand = random.randint(1, 100)
    
    #determine y range
    padding = r*1.5
    if playerN == 1:
        minY = int(padding)
        maxY = int(app.split - padding)
    else:
        minY = int(app.split + padding)
        maxY = int(app.height - padding)
    
    y = random.randint(minY, maxY)
    
    #spawn logic based on roll
    if rand < 10: 
        #10% chance for black hole
        obs = BlackHole(x, y, r, app.obstacleSpeed*0.8) #slightly slower
    elif rand < 40:
        #30% chance for star
        starType = random.randint(0, 4)
        obs = Star(x, y, r, app.obstacleSpeed, starType)
    else:
        #60% chance for standard obstacle (meteor or comet)
        imgType = random.choice(['images\meteor.png', 'images\comet.png'])
        obs = Obstacle(x, y, r, app.obstacleSpeed, img=imgType)
        
    if playerN == 1:
        app.p1Obstacles.append(obs)
    else:
        app.p2Obstacles.append(obs)

#helper for auto shoot powerup
def checkAutoShoot(app, player, bullets, obstacles):
    if not player.isAutoShoot:
        return
    if app.counter > player.autoShootTimeUp:
        player.isAutoShoot = False
        return
    if player.shootCooldown > 0: #fire every 10 frames for visibility
        player.shootCooldown -= 1
        return

    #updated target detection (target another enemy too)
    targets = []
    enemy = app.p2 if player == app.p1 else app.p1
    if player.y < app.split: #if in the upper universe
        targets += app.p1Obstacles
        if enemy.y < app.split:
            targets.append(enemy)
    else:
        targets += app.p2Obstacles #if in the lower universe
        if enemy.y >= app.split:
            targets.append(enemy)

    #find closest obstacles
    closestDist = app.width
    target = None
    for obs in targets:
        if isinstance(obs, Star) or isinstance(obs, BlackHole): continue
        
        d = distance(player.x, player.y, obs.x, obs.y)
        if d < closestDist:
            closestDist = d
            target = obs

    if target != None:
        angle = math.atan2(target.y - player.y, target.x - player.x)
        bSpeed = app.bulletSpeed*2.2
        dx = math.cos(angle)*bSpeed
        dy = math.sin(angle)*bSpeed
        
        minY = 0 if player.y < app.split else app.split
        maxY = app.split if player.y < app.split else app.height

        bSize = app.playerR*0.4
        bullets.append(Bullet(player.x, player.y, bSize, dx, dy, minY, maxY))
        player.shootCooldown = 10


#helper to check positions of bullets and obstacles
def updateObjects(app, bullets, obstacles):
    for i in range(len(bullets)-1, -1, -1):
        if not bullets[i].update(app.width): #off screen
            bullets.pop(i)
    
    for i in range(len(obstacles)-1, -1, -1):
        if not obstacles[i].update(): #off screen
            obstacles.pop(i)

def distance(x1, y1, x2, y2):
    return ((x1 - x2)**2 + (y1 - y2)**2)**0.5

def checkTeleportCollision(app, traveler, attackerBullets):
    for i in range(len(attackerBullets)-1, -1, -1):
        bullet = attackerBullets[i]
        if distance(bullet.x, bullet.y, traveler.x, traveler.y) < (traveler.r + bullet.r):
            attackerBullets.pop(i)
            
            if traveler.isTeleported:
                #travelers dies in another universe immediately if shot
                traveler.score = -100 
            else:
                #in own universe, players has only 30 points damage if shot
                traveler.takeDamage(30)
            return 

#helper to check collisions
def checkCollisions(app, player, bullets, obstacles):
    
    #1. bullet hits obstacle
    for i in range(len(bullets)-1, -1, -1):
        bullet = bullets[i]
        hit = False
        for j in range(len(obstacles)-1, -1, -1):
            obs = obstacles[j]
            if distance(bullet.x, bullet.y, obs.x, obs.y) < (obs.r + bullet.r):
                if isinstance(obs, BlackHole):
                    #teleporting bullets
                    #finding from which universe obstacles we need
                    if obstacles == app.p1Obstacles:
                        targetL = app.p2Obstacles
                    elif obstacles == app.p2Obstacles:
                        targetL = app.p1Obstacles
                    
                    #searching for the last blackhole (if it exists) in the abother universe
                    targetBH = None
                    for k in range(len(targetL)-1, -1, -1):
                        if isinstance(targetL[k], BlackHole):
                            targetBH = targetL[k]
                            break
                    
                    if targetBH:
                        bullet.x =  targetBH.x + targetBH.r + bullet.r
                        bullet.y = targetBH.y
                        bullet.dx = -bullet.dx #inverts the direction of the bullet
                        bullet.dy = 0
                        hit = False #don't delete bullet
                        break
                
                #bullets only destroy damaging obstacles, not stars/portals
                if not isinstance(obs, Star) and not isinstance(obs, BlackHole):
                    obstacles.pop(j)
                    hit = True
                    break 
        if hit:
            bullets.pop(i)
            
    #2. player hits obstacle
    for j in range(len(obstacles)-1, -1, -1):
        obs = obstacles[j]
        if distance(player.x, player.y, obs.x, obs.y) < (player.r + obs.r):
            #handle different collisions types
            if isinstance(obs, Star):
                player.collectedStars.add(obs.starType)
                if len(player.collectedStars) >= 2:
                    #powerup for collecting a constellation
                    player.isAutoShoot = True
                    player.autoShootTimeUp = app.counter + (15 * app.stepsPerSecond)
                    player.collectedStars.clear() #reset collection
                obstacles.pop(j)
                
            elif isinstance(obs, BlackHole):
                if app.counter < player.teleportCooldown:
                    continue

                obstacles.pop(j)
                
                if player.isTeleported:
                    #going home
                    player.isTeleported = False
                    player.teleportCooldown = app.counter + (1 * app.stepsPerSecond)
                    
                    player.minY = player.homeMinY
                    player.maxY = player.homeMaxY


                    player.x = app.playerX 
                    player.y = (player.homeMinY + player.homeMaxY)/2
                else:
                    #telepoting to another universe
                    player.isTeleported = True
                    player.teleportTimeUp = app.counter + (10 * app.stepsPerSecond)
                    player.teleportCooldown = app.counter + (2 * app.stepsPerSecond)
                    
                    if player == app.p1:
                        targetMinY = app.p2.homeMinY
                        targetMaxY = app.p2.homeMaxY
                    else:
                        targetMinY = app.p1.homeMinY
                        targetMaxY = app.p1.homeMaxY
                    
                    player.minY = targetMinY
                    player.maxY = targetMaxY

                    player.x = app.width - app.playerX
                    player.y = random.randint(int(targetMinY + player.r), int(targetMaxY - player.r))
                
            else:
                obstacles.pop(j)
                player.takeDamage(obs.damage)

def onKeyPress(app, key):
    if key == 'r':
        reset(app)
    if key == 'p':
        app.paused = not app.paused
    if app.paused or app.gameOver:
        return
        
    #bullet size
    bSize = app.playerR*0.4
    #generate bullets


    if app.myRole == 1:
        if app.p1.y < app.split:
            p1MinY, p1MaxY = 0, app.split
        else:
            p1MinY, p1MaxY = app.split, app.height
        
        if key == 'd':
            b = Bullet(app.p1.x + app.p1.r, app.p1.y, bSize, app.bulletSpeed, 0, p1MinY, p1MaxY)
            app.p1Bullets.append(b)
        if key == 'a':
            b = Bullet(app.p1.x - app.p1.r, app.p1.y, bSize, -app.bulletSpeed, 0, p1MinY, p1MaxY)
            app.p1Bullets.append(b)
        
    elif app.myRole == 2:
        if app.p2.y < app.split:
            p2MinY, p2MaxY = 0, app.split
        else:
            p2MinY, p2MaxY = app.split, app.height

        if key == 'right':
            b = Bullet(app.p2.x + app.p2.r, app.p2.y, bSize, app.bulletSpeed, 0, p2MinY, p2MaxY)
            app.p2Bullets.append(b)
        if key == 'left':
            b = Bullet(app.p2.x - app.p2.r, app.p2.y, bSize, -app.bulletSpeed, 0, p2MinY, p2MaxY)
            app.p2Bullets.append(b)
    

def onKeyHold(app, keys):
    if app.paused or app.gameOver:
        return
    
    dy = app.dy
    
    if app.myRole == 1:
        if 'w' in keys: app.p1.move(-dy)
        if 's' in keys: app.p1.move(dy)
    elif app.myRole == 2:
        if 'up' in keys: app.p2.move(-dy)
        if 'down' in keys: app.p2.move(dy)

def drawHealthBar(app, score, x, y):
    drawRect(x, y, app.barWidth, app.barHeight, fill=None, border=white)
    
    fillPct = max(1, min(100, score))/100
    fillW = app.barWidth*fillPct
    
    color = green
    if score < 30: color = red
    elif score < 60: color = yellow
        
    drawRect(x, y, fillW, app.barHeight, fill=color)

def drawObstacle(obs):
    if obs.img is not None:
        if type(obs)==Obstacle and obs.img=='images\comet.png':
            drawImage(obs.img, obs.x, obs.y, align='center', width=obs.r*4.5, height=obs.r*2)
        else:
            drawImage(obs.img, obs.x, obs.y, align='center', width=obs.r*3, height=obs.r*3)
        
    else:
        drawCircle(obs.x, obs.y, obs.r, fill=red)

def redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill=black)
    drawLine(0, app.split, app.width, app.split, fill=white, lineWidth=3)
    
    #draw player 1 and their obstacles
    drawCircle(app.p1.x, app.p1.y, app.p1.r, fill=app.p1.color)
    for b in app.p1Bullets:
        drawRect(b.x, b.y-b.r/2, b.r*3, b.r, fill=yellow)
    for obs in app.p1Obstacles:
        drawObstacle(obs)
    
    #draw player 2 and their obstacles
    drawCircle(app.p2.x, app.p2.y, app.p2.r, fill=app.p2.color)
    for b in app.p2Bullets:
        drawRect(b.x, b.y-b.r/2, b.r*3, b.r, fill=yellow)
    for obs in app.p2Obstacles:
        drawObstacle(obs)

    p1LabelX = app.width - app.margin - app.barWidth - 20
    p1BarX = app.width - app.margin - app.barWidth
    p1Y = app.height*0.05
    p2Y = app.split + app.height*0.05
    labelSize = app.height*0.04
    
 
    drawLabel("P1", p1LabelX, p1Y + app.barHeight/2, fill=white, size=labelSize)
    drawHealthBar(app, app.p1.score, p1BarX, p1Y)
    drawLabel(f"Stars: {len(app.p1.collectedStars)}/5", p1BarX, p1Y + app.barHeight + 15, fill=yellow, size=12, align='left')
    
    drawLabel("P2", p1LabelX, p2Y + app.barHeight/2, fill=white, size=labelSize)
    drawHealthBar(app, app.p2.score, p1BarX, p2Y)
    drawLabel(f"Stars: {len(app.p2.collectedStars)}/5", p1BarX, p2Y + app.barHeight + 15, fill=yellow, size=12, align='left')

    if app.p1.isAutoShoot:
        drawLabel("Auto-Shoot ACTIVE!!", p1BarX, p1Y + 50, fill=red, bold=True, align='left')
    if app.p2.isAutoShoot:
        drawLabel("Auto-Shoot ACTIVE!!", p1BarX, p2Y + 50, fill=red, bold=True, align='left')
    
    if app.paused or app.gameOver:
        drawRect(0, 0, app.width, app.height, fill='black', opacity=50)
        
        popupW = app.width*0.4
        popupH = app.height*0.3
        cx, cy = app.width/2, app.height/2
        
        drawRect(cx - popupW/2, cy - popupH/2, popupW, popupH, fill=white, border=purple, borderWidth=4)
        
        tSize = int(app.height*0.05)
        if app.gameOver:
            drawLabel("game over ^_^", cx, cy - popupH*0.15, fill=red, size=tSize, bold=True)
            drawLabel(f"{app.winner} wins!!", cx, cy + popupH*0.15, fill=black, size=tSize*0.8)
        else:
            drawLabel("paused...", cx, cy, size=tSize, bold=True, fill=black)

runApp(800, 600)