
import re

def getStringHumps(value):
    if len(value) == 0:
        return ''

    value = re.sub('[^a-zA-Z]+', '_', value)

    # Remove upper case characters in the middle of other upper case characters
    # Without this, for fully capitalized words we have to type in each letter
    value = re.sub("([^A-Z]?)([A-Z])([A-Z]+)([A-Z])([^A-Z]?)", "\\1\\2\\4\\5", value)

    if value[0] == '_':
        value = value[1:]

    if len(value) == 0:
        return ''

    if value[len(value) - 1] == '_':
        value = value[:-1]

    result = value[0].lower()
    i = 1

    while i < len(value):
        c = value[i]

        if c == '_':
            result += value[i+1].lower()
            i += 2
            continue

        if c.isupper():
            result += c.lower()

        i += 1

    return result

if __name__ == "__main__":

    def assertIsEqual(left, right):
        if left != right:
            raise Exception(f'Expected "{left}" to be equal to "{right}"')

    assertIsEqual(getStringHumps("readMe"), "rm")
    assertIsEqual(getStringHumps("read_me"), "rm")
    assertIsEqual(getStringHumps("read_Me"), "rm")
    assertIsEqual(getStringHumps("read_MEE"), "rme")
    assertIsEqual(getStringHumps("read4252-.'me10][\`.,,/><"), "rm")
    assertIsEqual(getStringHumps("readMEEEee"), "rme")
    assertIsEqual(getStringHumps("NIAPLog"), "nl")
    assertIsEqual(getStringHumps("this.is.a.test"), "tiat")
    assertIsEqual(getStringHumps("this.is.a.test"), "tiat")
    assertIsEqual(getStringHumps("_31./"), "")

    print("Tests passed")

