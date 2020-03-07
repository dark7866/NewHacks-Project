from tika import parser

rawText = parser.from_file('sample.pdf')

rawList = rawText['content']

rawList = rawList.replace('\n\n', '\n')

rawList=rawList.strip()

text_file=open("Output.txt", "w")
text_file.write(rawList)
text_file.write("\n")
text_file.close()