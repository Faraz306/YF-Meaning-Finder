##YF Meaning Finder, a New app to change finding files in hours into seconds!

##  Hello, I am the Founder of a small company named YF. I am 10. I built YF Meaning finder.

## Now, I am gonna tell you how I built this app:

### 1. The user first input the thing in the files for example: "the file had 14 app ideas" and chooses a location like: "C:/User/UserName/Downloads".

### 2. The app will use something to scan fast, scanning only .py, .txt, .csv, .md, and more. it won't read files formats like videos or images as it is not UTF-8 and it would lag the computer.

### 3. it finds the files and gives to Gemini (google.genai). before giving to gemini, it uses regex and scrubadub to filter out private data like api keys, and numbers.

### 4. Gemini (google.genai) will mark files as Yes or no like for example if the user said a text file with plan, gemini will look at the query and tell either Yes or No and i won't use sklearn because first thing we need a lots of data and then make it accurate, which makes it way more complex and might break past 268MB+. 

### 5. The app automatically opens the first 5 files in notepad automatically.
