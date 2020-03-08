import docx
# pip install python-docx

file_name = input("Please give me a word document file name: ")


def wordtotext(name):
    doc = docx.Document(name)

    text = ''
    for paragraph in doc.paragraphs:
        text += paragraph.text
        text += '\n'
    return text


text_file = open("Output.txt", "w")
text_file.write(wordtotext(file_name))
text_file.write('\n')
text_file.close()
