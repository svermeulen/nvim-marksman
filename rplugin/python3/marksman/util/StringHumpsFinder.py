
import re

def getStringHumps(value):
    if len(value) == 0:
        return ''

    value = re.sub('[^a-zA-Z]+', '_', value)

    if value[0] == '_':
        value = value[1:]

    if len(value) == 0:
        return ''

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

    assertIsEqual(getStringHumps("readMe"), "rm")
    assertIsEqual(getStringHumps("read_me"), "rm")
    assertIsEqual(getStringHumps("read_Me"), "rm")
    assertIsEqual(getStringHumps("read_MEE"), "rm")
    assertIsEqual(getStringHumps("read4252-.'me10][\`.,,/><"), "rm")
    assertIsEqual(getStringHumps("readMEEEe"), "rm")
    assertIsEqual(getStringHumps("this.is.a.test"), "tiat")
    assertIsEqual(getStringHumps("this.is.a.test"), "tiat")
    assertIsEqual(getStringHumps("_31./"), "")

    print("Tests passed")

