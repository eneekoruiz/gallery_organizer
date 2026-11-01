import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

bad_signature = "releaseMediaElement();pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {"
good_signature = "async function inlineCorrect(pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {\n    releaseMediaElement();"

# Also handle if async function inlineCorrect( is truncated
if bad_signature in content:
    content = content.replace("async function inlineCorrect(\n    " + bad_signature, good_signature)
    content = content.replace(bad_signature, "pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {\n    releaseMediaElement();")
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed broken function signature in index.html")
else:
    # Use direct regex/string replacement
    lines = content.split('\n')
    for i, l in enumerate(lines):
        if 'releaseMediaElement();pathEncoded' in l:
            lines[i-1] = "        async function inlineCorrect(pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {"
            lines[i] = "            releaseMediaElement();"
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("Fixed broken line using line iteration")
