import os
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import speedrun
import db
from datetime import datetime


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL = int(os.getenv('DISCORD_CHANNEL'))
OWNER = int(os.getenv('OWNER_ID'))
loop = asyncio.get_event_loop()

def getTime():
    return datetime.now()

def isItMondayMyDudes():
    now = datetime.now()
    weekday = now.weekday()
    # if weekday == 0 and now.hour >= 11 and now.hour < 13:
    if now.hour >= 11 and now.hour < 13:
        return True
    else:
        return False

async def backgroundUpdateTask():
    await bot.wait_until_ready()
    await asyncio.sleep(3600)
    while not bot.is_closed():
        try:
            print(getTime(), "Background update")
            users = db.getAllRunners()
            amountOfUsers = len(users)
            count = 0
            requestAmount = 0
            updatesToAnnounce = []
            for user in users:
                runs, updates = updateMember(user[0], isItMondayMyDudes())
                updatesToAnnounce = updatesToAnnounce + updates                
                requestAmount += 2 + runs
                count += 1                
                if requestAmount > 90 and count != amountOfUsers:                    
                    requestAmount = 0
                    await asyncio.sleep(30)
            print(getTime(), "update done")
            if len(updatesToAnnounce) > 0:
                loop.create_task(announceChanges(updatesToAnnounce))
            await asyncio.sleep(7200)
        except Exception as e:
            print(getTime(), "update failed", str(e))
            await asyncio.sleep(7200)



def updateMember(userId, monday=False, shout=True):
    updates = []
    if userId:
        bests = speedrun.getBest(userId)
        if bests:
            pb = speedrun.parsePB(bests, userId)
            old = db.getUserruns(userId)
            oldids = [x[0] for x in old]
            for run in pb:
                if run["runid"] not in oldids:
                    # print(name, run["game"], run["category"], run["place"])
                    for oldrun in old:
                        if oldrun[3] == run["game"] and oldrun[4] == run["category"]:
                            db.deleterun(oldrun[0])
                    db.insertrun(run)
                    if shout:
                        loop.create_task(announceRun(run))
                else:
                    oldrun = next((item for item in old if item[0] == run["runid"]), None)
                    # for oldrun in old:
                    if monday:
                        db.updaterun(run)
                        if shout and oldrun[2] != run["place"]:
                            updates.append(getChangeString(run, oldrun[2] - run["place"]))
            return (len(pb), updates)
    return (0, updates)

def replace_discord_char(text):
    text = text.replace("*", "\*")
    text = text.replace("_", "\_")
    return text

async def announceRun(run):
    channel = bot.get_channel(CHANNEL)
    name = replace_discord_char(db.getRunnerName(run["userid"]))
    await channel.send('New run! {} is now rank {}/{} in {} {} with a time of {}\n<{}>'.format(name, run["place"], run["totalruns"], run["game"], run["category"], run["time"], run["link"]))

async def announceChange(run, change):
    channel = bot.get_channel(CHANNEL)
    name = replace_discord_char(db.getRunnerName(run["userid"]))
    if change > 0:
        await channel.send('{} has risen to rank {}/{} in {} {}. Changed {} place(s)'.format(name, run["place"], run["totalruns"], run["game"], run["category"], change))
    else:
        await channel.send('{} has dropped to rank {}/{} in {} {}. Changed {} place(s)'.format(name, run["place"], run["totalruns"], run["game"], run["category"], change))

async def announceChanges(changeList):
    msg = ""
    channel = bot.get_channel(CHANNEL)
    print(getTime(), changeList)
    for announcement in changeList:
        msg = msg + announcement + "\n> \n"
        if len(msg) > 1700:
            await channel.send(msg.rstrip("> \n"))
            msg = ""
    if msg != "":
        await channel.send(msg.rstrip("> \n"))

def getChangeString(run, change):
    name = db.getUserName(run["userid"])
    if change > 0:
        return '> {} has risen to rank {}/{} in {} {}. Changed {} place(s)'.format(name, run["place"], run["totalruns"], run["game"], run["category"], change)
    else:
        return '> {} has dropped to rank {}/{} in {} {}. Changed {} place(s)'.format(name, run["place"], run["totalruns"], run["game"], run["category"], change)


async def check_silent_updates():
    print(getTime(), "Run silent update")
    users = db.getAllRunners()
    count = 0
    requestAmount = 0
    amountOfUsers = len(users)
    for user in users:
        runs, _ = updateMember(user[0], False, False)
        requestAmount += 2 + runs
        count += 1
        if count % 10 == 0:
            print(getTime(), "{}/{} members updated. Requests: {}".format(count, amountOfUsers, requestAmount))
        if requestAmount > 90 and count != amountOfUsers:
            print(getTime(), "Approaching rate limit. Time to sleep")
            requestAmount = 0
            await asyncio.sleep(30)
    print(getTime(), "update done")

bot = commands.Bot(command_prefix='/')

@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD:
            break

    print(getTime(),
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )
    print(getTime(), "guild has {} members\n".format(guild.member_count))
    loop.create_task(check_silent_updates())


@bot.command(name='update', help='Checks for new runs in speedrun.com')
async def checkUpdates(ctx):
    print(getTime(), "Run update")
    users = db.getAllRunners()
    await ctx.send("Will now check for new runs")
    count = 0
    requestAmount = 0
    amountOfUsers = len(users)
    updatesToAnnounce = []
    for user in users:
        runs, updates = updateMember(user[0])
        updatesToAnnounce = updatesToAnnounce + updates
        requestAmount += 2 + runs
        count += 1
        if count % 10 == 0:
            print(getTime(), "{}/{} members updated. Requests: {}".format(count, amountOfUsers, requestAmount))
        if requestAmount > 90 and count != amountOfUsers:
            print(getTime(), "Approaching rate limit. Time to sleep")
            requestAmount = 0
            await asyncio.sleep(30)
    print(getTime(), "update done")
    if len(updatesToAnnounce) > 0:
        loop.create_task(announceChanges(updatesToAnnounce)) 

@bot.command(name='drop_table', help='Drops all runs and fetches again. Will not shout')
async def renewRuns(ctx):
    if ctx.message.author.id == OWNER:
        print(getTime(), "Run update")
        users = db.getAllRunners()
        db.dropRuns()
        db.createTables()
        await ctx.send("Will reacquire runs")
        count = 0
        requestAmount = 0
        amountOfUsers = len(users)
        for user in users:
            runs, _ = updateMember(user[0], False, False)
            requestAmount += 2 + runs
            count += 1
            if count % 10 == 0:
                print(getTime(), "{}/{} members reloaded".format(count, amountOfUsers))
            if requestAmount > 90 and count != amountOfUsers:
                print(getTime(), "Approaching rate limit. Time to sleep")
                requestAmount = 0
                await asyncio.sleep(30)
        print(getTime(), "update done")
    else:
        await ctx.send("You don't have rights for this function")

@bot.command(name='runlist', help='/runlist <name>: lists all runs that person has. No name will list all runs on server')
async def sendRankings(ctx, name: str = ""):
    print(getTime(), "Run list called")
    if name:
        users = db.getRunner(name)
    else:
        if ctx.message.author.id != OWNER:
            await ctx.send("Needs a name")
            return
        users = db.getAllRunners()
        await ctx.send("This might take a while")
    if not users or len(users[0]) == 1:
        await ctx.send("I do not know this user. Try /follow <name> to add user to followed")
        return
    msg = ""
    for user in users:
        runs = db.getUserruns(user[0])
        if runs:
            msg = msg + "**{}**\n".format(user[1])
        for run in runs:
            #msg = msg + "> Rank {}/{}, ({}) on {} {}\n> WR {}\n".format(run[2], run[9], run[5], run[3], run[4], run[10])
            msg = msg + "> {} {}\n> \tRank {}/{}, ({})\n> \tWR {}\n".format(run[3], run[4], run[2], run[9], run[5], run[10])
            if len(msg) > 1700:
                await ctx.send(msg)
                msg = ""
    if msg != "":
        await ctx.send(msg)

@bot.command(name='follow', help='/follow <name> adds that name to be followed on speedrun.com')
async def follow(ctx, name : str = ""):
    print(getTime(), "Add user", name)
    if not name:
        await ctx.send("You need to give a name")
        return
    user = db.getRunner(name)
    if not user or len(user[0]) == 1:
        userSr = speedrun.getUser(name)
        if userSr:
            db.insertRunner(userSr["id"], name)
            await ctx.send("Will now follow {}".format(name))
            bests = speedrun.getBest(userSr["id"])
            if bests:
                pb = speedrun.parsePB(bests, userSr["id"])
                for run in pb:
                    db.insertrun(run)
        else:
            await ctx.send("Speedrun.com has no {}".format(name))
        print(getTime(), "Added user", name)
    else:
        await ctx.send("Already following {}".format(name))

@bot.command(name='unfollow', help='/unfollow <name> will stop following that guy')
async def unfollow(ctx, name : str = ""):
    print(getTime(), "Remoce user", name)
    if not name:
        await ctx.send("You need to give a name")
        return
    user = db.getRunner(name)
    if not user or len(user[0]) == 1:
        await ctx.send("I wasn't even following {}".format(name))
        return
    else:
        user = db.getRunner(name)
        db.deleteRunner(user[0][0])
        runs = db.getUserruns(user[0][0])
        for run in runs:
            db.deleterun(run[0])
        await ctx.send("Will now forget {}".format(name))

@bot.command(name='shutdown', help='Closes bot')
async def closeBot(ctx):

    if ctx.message.author.id == OWNER:
        await ctx.send("Bye bye")
        await ctx.bot.logout()

    else:
        await ctx.send("I'm sorry {}. I'm afraid I can't do that. ".format(ctx.message.author.name))

@bot.command(name='givgame', help='Gives random game from speedrun to run')
async def getRandomGame(ctx):
    print(getTime(), "Get random game")
    results = speedrun.getRandomGame()
    game = results[0]
    platform = results[1]
    category = results[2]
    runs = results[3]
    time = "Ei mittään"
    if(len(runs) > 0):
        wr = runs[0]
        time = speedrun.getTimeString(wr['run']["times"]["primary_t"])

    await ctx.send(f'{game["names"]["international"]} ({game["released"]}) {platform["name"]}\n' + \
        f'{category["name"]} WR: {time}\nRunners: {len(runs)}')

db.createTables()
bot.loop.create_task(backgroundUpdateTask())
bot.run(TOKEN)
