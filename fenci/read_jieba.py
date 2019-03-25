#MJ:以输入sentence为“中国民族伟大复兴为例”
"""
MJ_0
首先在initialize时加载一个字典,形如"词 词频 词性",产生一个FREQ的字典变量.
FREQ的key为词,value为词频.
FREQ会根据字典中的真词额外扩充一些中间状态词,中间状态词的特点是词频为0.
这些中间状态词作用于get_DAG*,具体见MJ_4.
"""

re_han_default = re.compile("([\u4E00-\u9FD5a-zA-Z0-9+#&\._%]+)", re.U)
re_skip_default = re.compile("(\r\n|\s)", re.U)
re_han_cut_all = re.compile("([\u4E00-\u9FD5]+)", re.U)
re_skip_cut_all = re.compile("[^a-zA-Z0-9+#\n]", re.U)
"""
MJ_1
\u4E00和\u9FD5分别对应unicode中的第一和最后一个中文字符。\u4E00-\u9FD5即所有中文字符。
re中所有的特殊字符在[]都无效，如果第一个字符是^表示取反。
"""

def cut(self, sentence, cut_all=False, HMM=True):
	'''
	The main function that segments an entire sentence that contains
	Chinese characters into seperated words.
	Parameter:
	- sentence: The str(unicode) to be segmented.
	- cut_all: Model type. True for full pattern, False for accurate pattern.
	- HMM: Whether to use the Hidden Markov Model.
	'''
	sentence = strdecode(sentence)     #MJ:将sentence解码为正确格式
	if cut_all:
		re_han = re_han_cut_all
		re_skip = re_skip_cut_all
	else:
		re_han = re_han_default
		re_skip = re_skip_default
	if cut_all:
		cut_block = self.__cut_all
	elif HMM:
		cut_block = self.__cut_DAG
	else:
		cut_block = self.__cut_DAG_NO_HMM
		blocks = re_han.split(sentence)
		"""
		MJ_2
		re_han 按正则切分sentence成groups。cut_all=True时，split出来的每个group仅为汉字/非汉字，而cut_all=False时，还能匹配字母数字'_+'等一些特殊符号。
		"""
	for blk in blocks:
		if not blk:
			continue
		if re_han.match(blk):
			for word in cut_block(blk):
			yield word
		else:
			tmp = re_skip.split(blk)
			"""
			MJ_3
			注意，re_skip_cut_all不含(),split时不会包含正则内容本身.
			这部分输出的是不能match re_han的词
			对于cut_all模式来说,输出的是不能match re_han的词中内容仅为[^a-zA-Z0-9+#\n]+的形式,注意最后的'+'不是误加的
			对于非cut_all模式,emm,输出所有不匹配的部分
			此外,以"阿QQ"为输入,在cut_all模式下为["阿","QQ"],非cut_all模式下为["阿Q","Q"],原因在于re_han_cut_all的匹配问题."Q"和"QQ"均在skip这个部分输出.
			"""
			for x in tmp:
				if re_skip.match(x):
					yield x
				elif not cut_all:
					for xx in x:
						yield xx
				else:
					yield x

"""
MJ_4
cut_block的各种实现都是基于get_DAG这个函数.DAG,有向无环图.
以"中华民国"为例,get_DAG的返回是{0: [0, 1, 3], 1: [1], 2: [2, 3], 3: [3]},值对应了加载字典中的所有词以及汉字本身.
它的实现就是通过MJ_0中所谓的中间状态词来完成的.
"""
def get_DAG(self, sentence):
	self.check_initialized()
	DAG = {}
	N = len(sentence)
	for k in xrange(N):
		tmplist = []
		i = k
		frag = sentence[k]
		while i < N and frag in self.FREQ:
			if self.FREQ[frag]:
				tmplist.append(i)
			i += 1
			frag = sentence[k:i + 1]
		if not tmplist:
			tmplist.append(k)
		DAG[k] = tmplist
	return DAG

"""
MJ_5
以最简单的_cut_all模式为例
old_j标记了当前匹配词的末尾位置的最大值
if那段,从这个位置开始匹配只能匹配到这个"汉字"本身,且还没被匹配过,则输出这个"汉字".汉字加""是因为还可能使字母数字等等
else那段,则是输出所有词并更新old_j.
"""
def __cut_all(self, sentence):
	dag = self.get_DAG(sentence)
	old_j = -1
	for k, L in iteritems(dag):
		if len(L) == 1 and k > old_j:
			yield sentence[k:L[0] + 1]
			old_j = L[0]
		else:
			for j in L:
				if j > k:
					yield sentence[k:j + 1]
					old_j = j

"""
MJ_6
__cut_DAG和__cut_DAG_NO_HMM没有看,应该额外还有很多细节的处理.
比如仍然以"阿QQQ"为例,它的get_DAG的返回值如果送给__cut_all其输出应该是,"阿","Q","Q","Q",但因为"QQQ"走的是cut函数中skip那条路,所以在cut_all模式下是["阿","QQQ"]
而如果cut函数中,re_han是re_han_default,而cut_block是__cut_all,那么输出应该是["阿Q","Q","Q"].但因为实际中__cut_DAG的一些细节,最后的输出是["阿Q","QQ"]
"""
def __cut_DAG_NO_HMM(self, sentence):
	DAG = self.get_DAG(sentence)
	route = {}
	self.calc(sentence, DAG, route)
	x = 0
	N = len(sentence)
	buf = ''
	while x < N:
		y = route[x][1] + 1
		l_word = sentence[x:y]
		if re_eng.match(l_word) and len(l_word) == 1:
			buf += l_word
			x = y
		else:
			if buf:
				yield buf
				buf = ''
			yield l_word
			x = y
	if buf:
		yield buf
		buf = ''

def __cut_DAG(self, sentence):
	DAG = self.get_DAG(sentence)
	route = {}
	self.calc(sentence, DAG, route)
	x = 0
	buf = ''
	N = len(sentence)
	while x < N:
		y = route[x][1] + 1
		l_word = sentence[x:y]
		if y - x == 1:
			buf += l_word
		else:
			if buf:
				if len(buf) == 1:
					yield buf
					buf = ''
				else:
					if not self.FREQ.get(buf):
						recognized = finalseg.cut(buf)
						for t in recognized:
							yield t
					else:
						for elem in buf:
							yield elem
					buf = ''
			yield l_word
		x = y

	if buf:
		if len(buf) == 1:
			yield buf
		elif not self.FREQ.get(buf):
			recognized = finalseg.cut(buf)
			for t in recognized:
				yield t
		else:
			for elem in buf:
				yield elem