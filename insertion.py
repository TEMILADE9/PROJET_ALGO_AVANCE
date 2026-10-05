def selection(liste):
	for i in range(len(liste)):
		min_i = i
		for j in range (i, len(liste)):
			if liste[j] < liste[min_i]:
				min_i = j
		liste[i], liste[min_i] = liste[min_i], liste[i]
	return liste
if __name__=="__main__":
	#liste = [1, 18, 9, -5]
	print(selection(liste))
