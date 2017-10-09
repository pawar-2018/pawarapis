import datetime as dt

def calculateSpendingDays(dateFormat, firstExpenditure):
    now = dt.datetime.now()
    then = dt.datetime.strptime(firstExpenditure, dateFormat)

    diff = now - then

    return diff.days


def calculateSpentPerDay(days, total):
    return total / days


def calculateSpentPerSecond(perDay):
    return perDay / 86400


# this just works because hours, minutes and seconds are easy to pluralize
def plural(word, count):
    res = word

    if count > 1:
        res += 's'
        
    return res