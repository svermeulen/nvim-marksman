
import re

def getStringHumps(value):
    value = re.sub('[^a-zA-Z]+', '_', value)

    if value[0] == '_':
        value = value[1:]

    if value[len(value) - 1] == '_':
        value = value[:-1]

    result = value[0].lower()
    lastIsUpper = value[0].isupper()
    i = 1

    while i < len(value):
        c = value[i]

        if c == '_':
            result += value[i+1].lower()
            lastIsUpper = value[i+1].isupper()
            i += 2
            continue

        if c.isupper() and c.isupper() != lastIsUpper:
            result += c.lower()

        lastIsUpper = c.isupper()
        i += 1

    return result

if __name__ == "__main__":

    def assertIsEqual(left, right):
        if left != right:
            raise Exception(f'Expected "{left}" to be equal to "{right}"')

    assertIsEqual(getHumps("readMe"), "rm")
    assertIsEqual(getHumps("read_me"), "rm")
    assertIsEqual(getHumps("read_Me"), "rm")
    assertIsEqual(getHumps("read_MEE"), "rm")
    assertIsEqual(getHumps("read4252-.'me10][\`.,,/><"), "rm")
    assertIsEqual(getHumps("readMEEEe"), "rm")
    assertIsEqual(getHumps("this.is.a.test"), "tiat")
    assertIsEqual(getHumps("this.is.a.test"), "tiat")

    print("Tests passed")

