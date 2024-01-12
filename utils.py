import base64
import pandas as pd

def create_onedrive_directdownload(onedrive_link):
  '''
  创建onedrive数据库url
  '''
  data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
  data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
  resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
  return resultUrl

def read_file(data):
  '''
  读取onedrive数据库(轻量级)
  '''
  df = pd.read_excel(data, sheet_name=1, converters={'盘口': str, '竞彩': str, '比分': str}, skiprows=[1, 50000]) # read last n rows for performance
  df['开球时间'] = df['开球时间'].fillna('')
  df['注释'] = df['注释'].fillna('')
  return df

def pct_to_float(pct):
  '''
  Convert percent String to float
  '''
  if isinstance(pct, str):
      return float(pct.strip('%'))/100
  return pct

def map_leagues(league):
  '''Last Edit: 12/26/2023'''
  league_dict = {
    '美职联':'USA Major League Soccer','日职联':'J1 League','德乙':'German Bundesliga 2','德甲':'German Bundesliga','西甲':'Spanish La Liga',
    '英超':'English Premier League','欧冠':'UEFA Champions League','阿甲':'Argentine Division 1','欧联':'UEFA Europa League','法甲':'France Ligue 1',
    '巴甲':'Brazil Serie A','意甲':'Italian Serie A','欧国联':'','墨超':'Primera Division Liga MX','葡超':'Liga Portugal 1','荷甲':'Holland Eredivisie',
    '英冠':'England Championship','解放者杯':'Copa Libertadores','欧预赛':'UEFA European Championship','瑞典超':'Swedish Allsvenskan',
    '挪超':'Norwegian Tippeligaen','南球杯':'Copa Sudamericana','世界杯':'','美洲杯':'','亚洲预选':'',
    '西乙':'Spanish La Liga 2','比甲':'Belgian Pro League','智甲':'','南美预选':'FIFA World Cup qualification (CONMEBOL)',
    '世预赛':'','北美预选':'','欧洲杯':'','欧协联':'UEFA Europa Conference League'}

  for key, value in league_dict.items():
    if league == key:
      league = league.replace(key, value)
  return league
    
def map_teams(team):
  '''Last Edit: 10/21/2023'''
  teams_dict = {
  #✔
  '美职联':{'Portland Timbers':'波特兰伐木者','Los Angeles FC':'洛杉矶FC','Minnesota United FC':'明尼苏达联','New England Revolution':'新英格兰革命',
          'DC United':'华盛顿联','San Jose Earthquakes':'圣何塞地震','Inter Miami CF':'迈阿密国际','FC Kansas City':'堪萨斯城体育','Austin FC':'奥斯汀FC',
          'Los Angeles Galaxy':'洛杉矶银河','St. Louis City':'圣路易斯城','Real Salt Lake':'皇家盐湖城','Colorado Rapids':'科罗拉多急流',
          'FC Dallas':'达拉斯FC','Seattle Sounders':'西雅图海湾人','Houston Dynamo':'休斯顿迪纳摩','Charlotte FC':'夏洛特FC','Montreal Impact':'蒙特利尔冲击',
          'Chicago Fire':'芝加哥火焰','Toronto FC':'多伦多FC','Vancouver Whitecaps':'温哥华白浪','Orlando City':'奥兰多城','Columbus Crew':'哥伦布机员',
          'Philadelphia Union':'费城联合','FC Cincinnati':'辛辛那提','Atlanta United':'亚特兰大联','New York City FC':'纽约城','New York Red Bulls':'纽约红牛',
          'Nashville':'纳什维尔'},
  #✔
  '日职联':{'Urawa Red Diamonds':'浦和红钻','Kyoto Sanga':'京都不死鸟','Yokohama Marinos':'横滨水手','Sagan Tosu':'鸟栖砂岩','Kawasaki Frontale':'川崎前锋',
          'FC Tokyo':'东京FC','Avispa Fukuoka':'福冈黄蜂','Nagoya Grampus':'名古屋逆戟鲸','Consadole Sapporo':'札幌冈萨多','Shonan Bellmare':'湘南海洋',
          'Hiroshima Sanfrecce':'广岛三箭','Vissel Kobe':'神户胜利船','Kashima Antlers':'鹿岛鹿角','Cerezo Osaka':'大阪樱花','Gamba Osaka':'大阪钢巴',
          'Albirex Niigata':'新泻天鹅','Yokohama FC':'横滨FC','Kashiwa Reysol':'柏太阳神'},
  #✔
  '德乙':{'Nurnberg':'纽伦堡','Greuther Furth':'菲尔特','SC Paderborn 07':'帕德博恩','SV Wehen Wiesbaden':'韦恩','Schalke 04':'沙尔克04','Magdeburg':'马格德堡',
        'Hansa Rostock':'罗斯托克','Fortuna Dusseldorf':'杜塞尔多夫','Karlsruher SC':'卡尔斯鲁厄','Kaiserslautern':'凯泽斯劳滕','SV Elversberg':'埃弗斯堡',
        'Hamburger SV':'汉堡','Hannover 96':'汉诺威96','VfL Osnabruck':'奥斯纳布吕克','Hertha Berlin':'柏林赫塔','Eintracht Braunschweig':'布伦瑞克',
        'St. Pauli':'圣保利','Holstein Kiel':'基尔'},
  #✔
  '德甲':{'Bayern Munchen':'拜仁慕尼黑','Bayer Leverkusen':'勒沃库森','VfL Bochum':'波鸿','Eintracht Frankfurt':'法兰克福','FC Koln':'科隆',
        'TSG Hoffenheim':'霍芬海姆','FSV Mainz 05':'美因茨','VfB Stuttgart':'斯图加特','RB Leipzig':'RB莱比锡','Augsburg':'奥格斯堡','SC Freiburg':'弗赖堡',
        'Borussia Dortmund':'多特蒙德','VfL Wolfsburg':'沃尔夫斯堡','Union Berlin':'柏林联合','Darmstadt':'达姆施塔特','Borussia Monchengladbach':'门兴格拉德巴赫',
        'Heidenheimer':'海登海姆','Werder Bremen':'云达不莱梅'},
  #✔
  '西乙':{'Burgos CF':'布尔戈斯','Eibar':'埃瓦尔','Real Oviedo':'皇家奥维耶多','Sporting Gijon':'希洪竞技','Tenerife':'特内里费','Albacete':'阿尔瓦塞特',
        'Leganes':'莱加内斯','SD Huesca':'韦斯卡','Real Valladolid':'巴拉多利德','Elche':'埃尔切','FC Cartagena':'卡塔赫纳','Real Zaragoza':'萨拉戈萨',
        'Mirandes':'米兰德斯','Andorra FC':'FC安道尔','Racing de Ferrol':'费罗尔竞技','Villarreal B':'比利亚雷亚尔B队','Racing Santander':'桑坦德竞技',
        'SD Amorebieta':'亚摩勒比塔','Eldense':'埃登斯','AD Alcorcon':'阿尔科孔','Levante':'莱万特','RCD Espanyol':'西班牙人'},
  #✔
  '西甲':{'Rayo Vallecano':'巴列卡诺','Alaves':'阿拉维斯','FC Barcelona':'巴塞罗那','Real Betis':'皇家贝蒂斯','Celta Vigo':'塞尔塔','Mallorca':'马略卡',
        'Valencia':'巴伦西亚','Atletico Madrid':'马德里竞技','Athletic Bilbao':'毕尔巴鄂竞技','Cadiz':'加迪斯','Real Madrid':'皇家马德里','Real Sociedad':'皇家社会',
        'Sevilla':'塞维利亚','Las Palmas':'拉斯帕尔马斯','Villarreal':'比利亚雷亚尔','Almeria':'阿尔梅里亚','Getafe':'赫塔费','Osasuna':'奥萨苏纳',
        'Granada CF':'格拉纳达','Girona':'赫罗纳'},
  #✔
  '英冠':{'Southampton':'南安普顿','Leicester City':'莱斯特城','Hull City':'赫尔城','Coventry City':'考文垂','Cardiff City':'卡迪夫城','Swansea City':'斯旺西',
        'Blackburn Rovers':'布莱克本','Middlesbrough':'米德尔斯堡','Bristol City':'布里斯托尔城','West Bromwich(WBA)':'西布朗','Huddersfield Town':'哈德斯菲尔德',
        'Rotherham United':'罗瑟汉姆','Norwich City':'诺维奇','Stoke City':'斯托克城','Preston North End':'普雷斯顿','Plymouth Argyle':'普利茅斯',
        'Queens Park Rangers (QPR)':'女王公园巡游者','Sunderland A.F.C':'桑德兰','Sheffield Wednesday':'谢菲尔德星期三','Ipswich Town':'伊普斯维奇',
        'Watford':'沃特福德','Birmingham City':'伯明翰','Millwall':'米尔沃尔','Leeds United':'利兹联'},
  #✔
  '英超':{'Newcastle United':'纽卡斯尔','Brentford':'布伦特福德','Aston Villa':'阿斯顿维拉','Crystal Palace':'水晶宫','Fulham':'富勒姆','Luton Town':'卢顿',
        'Manchester United':'曼联','Brighton Hove Albion':'布莱顿','Tottenham Hotspur':'热刺','Sheffield United':'谢菲尔德联','West Ham United':'西汉姆联',
        'Manchester City':'曼城','Wolves':'狼队','Liverpool':'利物浦','Everton':'埃弗顿','Arsenal':'阿森纳','AFC Bournemouth':'伯恩茅斯','Chelsea':'切尔西',
        'Nottingham Forest':'诺丁汉森林','Burnley':'伯恩利'},
  #✔
  '欧冠':{'FC Copenhagen':'哥本哈根','Galatasaray':'加拉塔萨雷','Red Bull Salzburg':'萨尔茨堡红牛','Celtic FC':'凯尔特人','Young Boys':'伯尔尼年轻人',
        'Crvena Zvezda':'贝尔格莱德红星','FC Shakhtar Donetsk':'顿涅茨克矿工'},
  #✔
  '欧联':{'Olympiakos Piraeus':'奥林匹亚科斯','Backa Topola':'托波拉','AEK Athens':'雅典AEK','Aris Limassol':'阿里斯利马索尔','Glasgow Rangers':'流浪者',
        'Sparta Praha':'布拉格斯巴达','Rakow Czestochowa':'琴斯托霍瓦','Sturm Graz':'格拉茨风暴','LASK Linz':'林茨','Maccabi Haifa':'海法马卡比',
        'Panathinaikos':'帕纳辛奈科斯','Servette':'塞尔维特','Sheriff Tiraspol':'蒂拉斯波尔警长','Slavia Praha':'布拉格斯拉维亚','Qarabag':'卡拉巴赫'},

  '欧协联':{'NK Olimpija Ljubljana':'卢布尔雅那奥林匹亚','Besiktas JK':'贝西克塔斯','Dinamo Zagreb':'萨格勒布迪纳摩','Lokomotiv Astana':'阿斯塔纳',
          'FC Viktoria Plzen':'比尔森胜利','KF Ballkani':'巴利卡尼','Lugano':'卢加诺','Maccabi Tel Aviv':'特拉维夫马卡比','Breidablik':'布列达布利克',
          'Slovan Bratislava':'布拉迪斯拉发','KI Klaksvik':'克拉克斯维克','Zorya':'索尔亚','Aberdeen':'阿伯丁','Fenerbahce':'费内巴切','Nordsjaelland':'北西兰',
          'Ferencvarosi TC':'费伦茨瓦罗斯','Cukaricki Stankom':'古拉瑞奇','HJK Helsinki':'赫尔辛基','PAOK Saloniki':'塞萨洛尼基','HSK Zrinjski Mostar':'莫斯塔尔兹林斯基',
          'Legia Warszawa':'华沙莱吉亚','Ludogorets Razgrad':'卢多戈雷茨','Spartak Trnava':'特纳瓦斯巴达','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},
  #✔
  '法甲':{'Paris Saint Germain (PSG)':'巴黎圣日耳曼','Nice':'尼斯','Lens':'朗斯','Metz':'梅斯','Rennes':'雷恩','Lille':'里尔','Lyon':'里昂',
        'Le Havre':'勒阿弗尔','Marseille':'马赛','Toulouse':'图卢兹','Clermont':'克莱蒙','Nantes':'南特','Reims':'兰斯','Stade Brestois':'布雷斯特',
        'Strasbourg':'斯特拉斯堡','Montpellier':'蒙彼利埃','Lorient':'洛里昂','Monaco':'摩纳哥'},
  #✔
  '意甲':{'Genoa':'热那亚','Napoli':'那不勒斯','Inter Milan':'国际米兰','AC Milan':'AC米兰','Juventus':'尤文图斯','Lazio':'拉齐奥','AS Roma':'罗马',
        'Empoli':'恩波利','Fiorentina':'佛罗伦萨','Atalanta':'亚特兰大','Frosinone':'弗罗西诺内','Sassuolo':'萨索洛','Monza':'蒙扎','Lecce':'莱切',
        'Cagliari':'卡利亚里','Udinese':'乌迪内斯','Verona':'维罗纳','Bologna':'博洛尼亚','Salernitana':'萨勒尼塔纳','Torino':'都灵'},

  '阿甲':{'Banfield':'班菲尔德','Argentinos Juniors':'阿根廷青年人','Colon de Santa Fe':'哥伦布竞技','Rosario Central':'罗萨里奥中央',
        'Defensa Y Justicia':'国防与司法','Boca Juniors':'博卡青年','Club Atletico Tigre':'老虎竞技','Estudiantes La Plata':'拉普拉塔大学生',
        'Independiente':'独立','CA Huracan':'飓风','Talleres Cordoba':'塔列雷斯','Instituto AC Cordoba':'科尔多瓦学院','Atletico Tucuman':'图库曼竞技',
        'Barracas Central':'巴拉卡斯中央','San Lorenzo':'圣洛伦索','Racing Club':'竞技','Newells Old Boys':'纽维尔老男孩','Club Atlético Unión':'圣菲联',
        'River Plate':'河床','Arsenal de Sarandi':'萨兰迪兵工厂','Godoy Cruz Antonio Tomba':'戈多伊克鲁斯','Belgrano':'贝尔格拉诺','Lanus':'拉努斯',
        'Sarmiento Junin':'萨米恩托','Gimnasia La Plata':'拉普拉塔体操','Central Cordoba SDE':'科尔多瓦中央','Velez Sarsfield':'萨斯菲尔德',
        'CA Platense':'普拉滕斯竞技'},
  #✔
  '巴甲':{'Palmeiras':'帕尔梅拉斯','Goias':'戈亚斯','Cuiaba':'奎尔巴','America MG':'米内罗美洲','Bragantino':'布拉甘蒂诺红牛','Gremio (RS)':'格雷米奥',
        'Atletico Mineiro':'米内罗竞技','Botafogo RJ':'博塔弗戈','Vasco da Gama':'瓦斯科达伽马','Fluminense RJ':'弗鲁米嫩塞','Corinthians Paulista (SP)':'科林蒂安',
        'Bahia':'巴伊亚','Santos':'桑托斯','Cruzeiro':'克鲁塞罗','Sao Paulo':'圣保罗','Fortaleza':'福塔莱萨','Flamengo':'弗拉门戈','Atletico Paranaense':'巴拉纳竞技',
        'Internacional RS':'巴西国际','Coritiba PR':'库里蒂巴'},
  #✔
  '墨超':{'Club Tijuana':'蒂华纳','Toluca':'托卢卡','Mazatlan FC':'马萨特兰','CDSyC Cruz Azul':'蓝十字','Club America':'美洲','Chivas Guadalajara':'瓜达拉哈拉',
        'Monterrey':'蒙特雷','Club Leon':'莱昂','Necaxa':'内卡萨','FC Juarez':'华雷斯','Atlas':'阿特拉斯','Tigres UANL':'墨西哥老虎','Queretaro FC':'克雷塔罗',
        'Puebla':'普埃布拉','Pumas U.N.A.M.':'美洲狮','Atletico San Luis':'圣路易斯','Pachuca':'帕丘卡','Santos Laguna':'桑托斯拉古纳'},

  '智甲':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '解放者杯':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '南球杯':{'Liga Dep. Universitaria Quito':'基多大学','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},
  #✔
  '荷甲':{'Heracles Almelo':'阿尔梅罗大力神','FC Utrecht':'乌德勒支','PSV Eindhoven':'埃因霍温','NEC Nijmegen':'奈梅亨','Fortuna Sittard':'锡塔德幸运',
        'Volendam':'福伦丹','Vitesse Arnhem':'维特斯','RKC Waalwijk':'瓦尔韦克','Feyenoord':'费耶诺德','SC Heerenveen':'海伦芬','AZ Alkmaar':'阿尔克马尔',
        'Sparta Rotterdam':'鹿特丹斯巴达','Excelsior SBV':'SBV精英','Almere City FC':'阿尔梅勒城','FC Twente Enschede':'特温特','AFC Ajax':'阿贾克斯',
        'PEC Zwolle':'兹沃勒','Go Ahead Eagles':'前进之鹰'},
  #✔
  '葡超':{'Moreirense':'莫雷拉人','Sporting Braga':'布拉加','Estrela da Amadora':'阿马多拉','FC Porto':'波尔图','Vizela':'维泽拉','Benfica':'本菲卡',
        'SC Farense':'法鲁人','Rio Ave':'阿维河','FC Famalicao':'法马利康','Sporting CP':'葡萄牙体育','Vitoria Guimaraes':'吉马良斯','Portimonense':'波尔蒂芒人',
        'FC Arouca':'阿罗卡','Casa Pia AC':'卡萨皮亚','Gil Vicente':'吉尔维森特','Estoril':'埃斯托里尔','Boavista FC':'博阿维斯塔','GD Chaves':'沙维斯'},
  #✔
  '瑞典超':{'Djurgardens':'佐加顿斯','IFK Varnamo':'瓦纳默','IFK Goteborg':'哥德堡','Brommapojkarna':'布洛马波卡纳','IK Sirius FK':'天狼星',
          'Varbergs BoIS FC':'瓦尔贝里','Elfsborg':'埃尔夫斯堡','Kalmar':'卡尔马','Hacken':'赫根','Halmstads':'哈尔姆斯塔德','Hammarby':'哈马比',
          'Malmo FF':'马尔默','AIK Solna':'索尔纳','Degerfors IF':'代格福什','IFK Norrkoping FK':'北雪平','Mjallby AIF':'米亚尔比'},
  #✔
  '挪超':{'Haugesund':'海于格松','Viking':'维京','Molde':'莫尔德','Odd Grenland':'奥特','Sandefjord':'桑德菲杰','Stromsgodset':'斯托姆加斯特',
        'Valerenga':'瓦勒伦加','Aalesund FK':'奥勒松','Rosenborg':'罗森博格','Bodo Glimt':'博多格林特','Sarpsborg 08':'萨普斯堡','Lillestrom':'利勒斯特罗姆',
        'Stabaek':'斯塔贝克','Brann':'布兰','Tromso IL':'特罗姆瑟','Ham-Kam':'汉坎'},
  #✔
  '比甲':{'Westerlo':'韦斯特洛','Royal Antwerp':'安特卫普','Club Brugge':'布鲁日','Charleroi':'沙勒鲁瓦','Saint Gilloise':'圣吉罗斯','Racing Genk':'亨克',
        'Jeunesse Molenbeek':'莫伦贝克','Cercle Brugge':'色格拉布鲁日','Sint-Truidense':'圣图尔登','Mechelen':'梅赫伦','Oud Heverlee':'奥哈瓦里',
        'KAA Gent':'根特','Kortrijk':'科特赖克','Anderlecht':'安德莱赫特','KAS Eupen':'欧本','Standard Liege':'标准列日'},

  'Asia':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  'America':{'Peru':'秘鲁','Brazil':'巴西','Chile':'智利','Colombia':'哥伦比亚','Venezuela':'委内瑞拉','Paraguay':'巴拉圭','Ecuador':'厄瓜多尔',
            'Uruguay':'乌拉圭','Bolivia':'玻利维亚','Argentina':'阿根廷'},

  'Europe':{'Bosnia-Herzegovina':'波黑','Croatia':'克罗地亚','Latvia':'拉脱维亚','Cyprus':'塞浦路斯','Scotland':'苏格兰','Luxembourg':'卢森堡',
          'Iceland':'冰岛','Slovakia':'斯洛伐克','Portugal':'葡萄牙','Turkey':'土耳其','Armenia':'亚美尼亚','Georgia':'格鲁吉亚','Spain':'西班牙',
          'Kosovo':'科索沃','Switzerland':'瑞士','North Macedonia':'马其顿','Italy':'意大利','Romania':'罗马尼亚','Israel':'以色列','Andorra':'安道尔',
          'Belarus':'白俄罗斯','Estonia':'爱沙尼亚','Sweden':'瑞典','Ukraine':'乌克兰','England':'英格兰','Azerbaijan':'阿塞拜疆','Belgium':'比利时',
          'Albania':'阿尔巴尼亚','Poland':'波兰','Greece':'希腊','Ireland':'爱尔兰','Netherlands':'荷兰','Lithuania':'立陶宛','Serbia':'塞尔维亚',
          'Slovenia':'斯洛文尼亚','Faroe Islands':'法罗群岛','Moldova':'摩尔多瓦','Finland':'芬兰','Denmark':'丹麦','Montenegro':'黑山',
          'Bulgaria':'保加利亚','Kazakhstan':'哈萨克斯坦','Northern Ireland':'北爱尔兰','Wales':'威尔士','France':'法国','Norway':'挪威',
          'Austria':'奥地利','Malta':'马耳他'},}

  for league_key, league_values in teams_dict.items():
    for key, value in league_values.items():
      if team == key:
        team = team.replace(key, value)
  return team

def clean_leagues(league_name):
  '''返回清洗后的联赛名称及是否属于收录的联赛'''
  league_dict = {'美职':'美职联','日职':'日职联','冠军杯':'欧冠','智利甲':'智甲','欧霸杯':'欧联','南俱杯':'南球杯','世美预':'南美预选'}

  league_list = ['美职联','日职联','德乙','德甲','西甲','英超','欧冠','阿甲','欧联','法甲','巴甲','意甲','欧国联',
                '墨超','葡超','荷甲','英冠','解放者杯','欧预赛','南球杯','瑞典超','挪超','世界杯','美洲杯','亚洲预选',
                '西乙','比甲','智甲','南美预选','世预赛','北美预选','欧洲杯','欧协联']
  
  for key, value in league_dict.items():
    league_name = league_name.replace(key, value)
      
  if league_name in league_list:
    return league_name, True
  else:
    return league_name, False
    
def clean_teams(home, away, league_name):
  '''
  返回清洗后的球队名称
  Last Edit: 11/30/2023
  '''
  teams_dict = {'日职联':{'鸟栖沙岩':'鸟栖砂岩','清水鼓动':'清水心跳','名古屋鲸八':'名古屋逆戟鲸'},
                '美职联':{'辛辛那提FC':'辛辛那提','温哥华白帽':'温哥华白浪','堪萨斯城竞技':'堪萨斯城体育','波特兰伐木工':'波特兰伐木者'},
                '阿甲':{'普拉腾斯':'普拉滕斯竞技','泰格雷':'老虎竞技','竞技俱乐部':'竞技','圣塔菲联':'圣菲联','巴拉卡斯中央队':'巴拉卡斯中央',
                        '科隆竞技':'哥伦布竞技','铁路工场':'塔列雷斯','阿尔多西维':'阿尔多希维','科尔多瓦中央SDE':'科尔多瓦中央','联合队':'科尔多瓦学院',
                        '阿根廷独立':'独立','萨尔米安杜':'萨米恩托','飓风队':'飓风','帕特罗纳图':'天主教青年','防御与正义':'国防与司法','天主教青年会':'天主教青年'},
                '德甲':{'莱比锡红牛':'RB莱比锡'},
                '西甲':{'维戈塞尔塔':'塞尔塔','马洛卡':'马略卡','阿尔梅利亚':'阿尔梅里亚','瓦拉多利德':'巴拉多利德','加的斯':'加迪斯'},
                '英超':{'南安普敦':'南安普顿','曼彻斯特联':'曼联','曼彻斯特城':'曼城','莱切斯特城':'莱斯特城','托特纳姆热刺':'热刺'},
                '法甲':{'巴黎圣日尔曼':'巴黎圣日耳曼'},
                '意甲':{'克雷莫纳':'克雷莫内塞','弗洛西诺尼':'弗罗西诺内'},
                '欧冠':{'比尔森':'比尔森胜利','萨尔茨堡':'萨尔茨堡红牛','格拉斯哥流浪者':'流浪者','年轻人':'伯尔尼年轻人'},
                '欧联':{'谢里夫':'蒂拉斯波尔警长','LASK林茨':'林茨','帕纳辛纳科斯':'帕纳辛奈科斯','利马索尔阿里斯':'阿里斯利马索尔'},
                '欧协联':{'第聂伯罗特警':'SK第聂伯罗','波兹南':'波兹南莱赫','比尔舒华夏普尔':'贝尔谢巴工人','萨尔格里斯':'扎尔吉里斯',
                        '布加勒斯特星队':'布加勒斯特星','列加斯':'里加足球学校','伊斯坦布':'伊斯坦布尔','利马索尔阿波罗':'阿波罗利马索尔',
                        '奥林比查':'卢布尔雅那奥林匹亚','泰拿华斯巴达':'特纳瓦斯巴达','萨连斯基':'莫斯塔尔兹林斯基','卢甘斯克黎明':'索尔亚','卡拉卡斯维克':'克拉克斯维克',
                        '贝雷达比历克':'布列达布利克'},
                '德乙':{'不伦瑞克':'布伦瑞克'},
                '英冠':{'加的夫城':'卡迪夫城','布里斯托城':'布里斯托尔城','西布罗姆维奇':'西布朗'},
                '西乙':{'格拉纳达GF':'格拉纳达','米兰迪斯':'米兰德斯','安道尔CF':'FC安道尔','阿尔巴切特':'阿尔瓦塞特','特內里费':'特内里费','艾科坎':'阿尔科孔',
                        '费路尔':'费罗尔竞技', '艾尔德斯':'埃登斯'},
                '巴甲':{'奥瓦':'阿瓦伊','科里蒂巴':'库里蒂巴','布拉干蒂诺RB':'布拉甘蒂诺红牛','戈伊亚斯':'戈亚斯','福塔雷萨':'福塔莱萨','库亚巴':'奎尔巴'},
                '墨超':{'老虎大学':'墨西哥老虎','马萨特兰FC':'马萨特兰','蒙特瑞':'蒙特雷','墨西哥美洲':'美洲','阿苏尔':'蓝十字',
                        '拿加沙':'内卡萨','圣路易斯竞技':'圣路易斯','提华纳':'蒂华纳'},
                '葡超':{'波尔蒂芒尼斯':'波尔蒂芒人','沙维什':'沙维斯','吉维森特':'吉尔维森特','里奥阿维':'阿维河','里斯本竞技':'葡萄牙体育',
                        '卡沙比亞':'卡萨皮亚','维兹拉':'维泽拉','费雷拉':'帕索斯费雷拉','马里迪莫':'马德拉航海','摩雷伦斯':'莫雷拉人','法伦斯':'法鲁人'},
                '荷甲':{'埃门':'埃蒙','福图纳锡塔德':'锡塔德幸运','PSV埃因霍温':'埃因霍温','维迪斯':'维特斯','赫拉克勒斯':'阿尔梅罗大力神'},
                '瑞典超':{'韦纳穆':'瓦纳默','IFK哥德堡':'哥德堡','AIK索尔纳':'索尔纳','布鲁马波卡纳':'布洛马波卡纳'},
                '挪超':{'奥德':'奥特','博德闪耀':'博多格林特','格里姆斯塔':'谢夫','桑纳菲尤尔':'桑德菲杰','萨尔普斯堡':'萨普斯堡'},
                '比甲':{'奥德赫维里':'奥哈瓦里','聚尔特瓦雷赫姆':'威尔郡','沙勒罗瓦':'沙勒鲁瓦','瑟兰联':'塞莱恩','吉马雷斯':'吉马良斯'},
                '智甲':{'尤尼昂':'拉卡勒拉联','科金博':'科金博联合','维尼亚德马埃弗顿':'比尼亚德尔马埃弗顿','库里科':'库里科联合','马加拉内斯':'麦哲伦',
                        '塞雷那':'拉塞雷纳','纽夫莱恩斯':'纽布伦斯','希金斯':'奥希金斯','科布雷索':'科布雷萨尔','奥达斯':'奥达科斯意大利人','华奇巴托':'瓦奇巴托'},
                '解放者杯':{'万卡约':'万卡约体育','巴拉圭国民':'亚松森国民','水晶体育':'水晶竞技','曼特宁独立':'麦德林独立','时刻准备':'时刻准备着','麦罗波利塔诺':'大都会',
                          '蒙得维的亚国民':'乌拉圭民族','国民体育会':'国民竞技','瓜亚基尔':'巴塞罗那SC','佩雷拉':'佩雷拉体育','蒙得维的':'利物浦','亚松森自由':'自由',
                          '亚松森奥林匹亚':'奥林匹亚'},
                '南球杯':{'德尔瓦耶独立':'山谷独立','卡巴列罗':'卡巴雷罗将军','港发院':'卡贝略港大学','利加大学':'基多大学','德芬':'海豚','奥利恩特':'东方石油',
                          '丹奴比奥':'多瑙河','亚松森瓜拉尼':'巴拉圭瓜拉尼','艾美利亚诺体育':'阿梅利亚诺体育','艾斯图第安特':'梅里达大学生','塔奇拉':'塔齐拉体育',
                          '阿古拉斯多拉达斯':'里奥内格罗老鹰','卡萨大学队':'卡萨大学','普诺双国':'两国竞技','帕马科亚':'棕榈竞技','昆卡':'昆卡体育','托利马体育':'托里马体育',
                          '大学生体育':'秘鲁体育大学'},
                '世界杯':{'沙特':'沙特阿拉伯'}
                }
  
  for league_key, league_values in teams_dict.items():
    for key, value in league_values.items():
      if home == key:
        home = home.replace(key, value)
      if away == key:
        away = away.replace(key, value)
  return home, away