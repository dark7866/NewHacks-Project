from tika import parser
import glob

pdf_list = glob.glob("*pdf")

rawText = parser.from_file(pdf_list[0])

rawList = rawText['content']

rawList = rawList.replace('\n\n', '\n')

rawList=rawList.strip()

text_file=open("Output.txt", "w")
text_file.write(rawList)
text_file.write("\n")
text_file.close()