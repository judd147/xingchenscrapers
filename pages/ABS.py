# -*- coding: utf-8 -*-
"""
Last Edit 9/12/2023
@author: zhangliyao
Asian Handicap scraper with Streamlit
"""

league_dict = {
  '美职联':'USA Major League Soccer','日职联':'','德乙':'','德甲':'','西甲':'','英超':'','欧冠':'',
  '阿甲':'','欧联':'','法甲':'','巴甲':'','意甲':'','欧国联':'','墨超':'','葡超':'Liga Portugal 1','荷甲':'',
  '英冠':'','解放者杯':'','欧预赛':'UEFA European Championship','南球杯':'','瑞典超':'','挪超':'',
  '世界杯':'','美洲杯':'','亚洲预选':'','西乙':'Spanish La Liga 2','比甲':'','智甲':'',
  '南美预选':'FIFA World Cup qualification (CONMEBOL)','世预赛':'','北美预选':'','欧洲杯':'','世俱杯':'','欧协联':''}

teams_dict = {
  '葡超':{'Moreirense':'莫雷拉人','Sporting Braga':'布拉加','':'','':'','':'','':''},

  '美职联':{'Portland Timbers':'波特兰伐木者','Los Angeles FC':'洛杉矶FC','Minnesota United FC':'明尼苏达联','New England Revolution':'新英格兰革命',
          'DC United':'华盛顿联','San Jose Earthquakes':'圣何塞地震','Inter Miami CF':'迈阿密国际','FC Kansas City':'堪萨斯城体育',
          'Los Angeles Galaxy':'洛杉矶银河','St. Louis City':'圣路易斯城','':'','':'','':'','':''},

  '日职联':{},

  '德乙':{},

  '德甲':{},

  '西乙':{'Burgos CF':'布尔戈斯','Eibar':'埃瓦尔','Real Oviedo':'皇家奥维耶多','Sporting Gijon':'希洪竞技','Tenerife':'特内里费','Albacete':'阿尔瓦塞特',
        'Leganes':'莱加内斯','SD Huesca':'韦斯卡','Real Valladolid':'巴拉多利德','Elche':'埃尔切','FC Cartagena':'卡塔赫纳','Real Zaragoza':'萨拉戈萨',
        'Mirandes':'米兰德斯','Andorra FC':'FC安道尔','Racing de Ferrol':'','Villarreal B':'比利亚雷亚尔B队','Racing Santander':'桑坦德竞技',
        'SD Amorebieta':'亚摩勒比塔','Eldense':'埃登斯','AD Alcorcon':'阿尔科孔'},

  '西甲':{},

  '英冠':{},

  '英超':{},

  '欧冠':{},

  '欧联':{},

  '欧协联':{},

  '法甲':{},

  '意甲':{},

  '阿甲':{},

  '巴甲':{},

  '墨超':{},

  '荷甲':{},

  '解放者杯':{},

  '南球杯':{},

  '瑞典超':{},

  '挪超':{},

  '比甲':{},

  '智甲':{},

  'Asia':{},

  'America':{'Peru':'秘鲁','Brazil':'巴西','Chile':'智利','Colombia':'哥伦比亚','Venezuela':'委内瑞拉','Paraguay':'巴拉圭','Ecuador':'厄瓜多尔',
          'Uruguay':'乌拉圭','Bolivia':'玻利维亚','Argentina':'阿根廷'},

  'Europe':{'Bosnia-Herzegovina':'波黑','Croatia':'克罗地亚','Latvia':'拉脱维亚','Cyprus':'塞浦路斯','Scotland':'苏格兰','Luxembourg':'卢森堡',
          'Iceland':'冰岛','Slovakia':'斯洛伐克','Portugal':'葡萄牙','Turkey':'土耳其','Armenia':'亚美尼亚','Georgia':'格鲁吉亚','Spain':'西班牙',
          'Kosovo':'科索沃','Switzerland':'瑞士','North Macedonia':'马其顿','Italy':'意大利','Romania':'罗马尼亚','Israel':'以色列','Andorra':'安道尔',
          'Belarus':'白俄罗斯','Estonia':'爱沙尼亚','Sweden':'瑞典','Ukraine':'乌克兰','England':'英格兰','Azerbaijan':'阿塞拜疆','Belgium':'比利时',
          'Albania':'阿尔巴尼亚','Poland':'波兰','Greece':'希腊','Ireland':'爱尔兰','Netherlands':'荷兰','Lithuania':'立陶宛','Serbia':'塞尔维亚',
          'Slovenia':'斯洛文尼亚','Faroe Islands':'法罗群岛','Moldova':'摩尔多瓦','Finland':'芬兰','Denmark':'丹麦','Montenegro':'黑山',
          'Bulgaria':'保加利亚','Kazakhstan':'哈萨克斯坦','Northern Ireland':'北爱尔兰','Wales':'威尔士','France':'法国','Norway':'挪威',
          'Austria':'奥地利','Malta':'马耳他'},

}#Last Edit: 9/12/2023