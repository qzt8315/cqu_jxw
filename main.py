import requests
import re
import hashlib
from lxml import etree

class User:
    (OFFLINE,ONLINE,UNKNOW)=range(3)
    urls = [r'http://202.202.1.176:8080', r'http://222.198.128.126', r'http://202.202.1.41']
    # 登陆教学网的网址
    curl = urls[0]
    Uid = None
    uname = ''
    password = None
    state = OFFLINE
    schoolcode = None
    headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
        }
    parameters = {}
    cookies = {}
    re_getviewstate = re.compile(r'VIEWSTATE"\svalue="[^"]+"')
    re_getviewstategenerator= re.compile(r'VIEWSTATEGENERATOR"\svalue="[^"]+"')
    re_getUserIdName = re.compile(r'\d*\][^<]+')
    re_getCourseTable = re.compile(r'<TABLE\sid=oTable.*?</table>')
    courses = {}
    

    def __init__(self, Uid, password, schoolcode='10611'):
        self.Uid = Uid
        self.password = password
        self.schoolcode = schoolcode

        self.login()

    def login(self):
        # 获取必要的信息
        r = requests.get(self.curl + '/_data/index_login.aspx', headers = self.headers)
        self.cookies['safedog-flow-item'] = r.cookies['safedog-flow-item']
        self.cookies['ASP.NET_SessionId'] = r.cookies['ASP.NET_SessionId']
        self.cookies['_D_SID'] = r.cookies['_D_SID']
        self.parameters['__VIEWSTATE'] = self.re_getviewstate.findall(r.text)[0].split('"')[-2]
        self.parameters['__VIEWSTATEGENERATOR'] =self.re_getviewstategenerator.findall(r.text)[0].split('"')[-2]
        self.parameters['Sel_Type'] = 'STU'
        self.parameters['txt_dsdsdsdjkjkjc'] = self.Uid
        self.parameters['efdfdfuuyyuuckjg'] = self.passwordEncryption(self.Uid, self.password, self.schoolcode)
        self.parameters['txt_dsdfdfgfouyy'] = ''
        self.parameters['txt_ysdsdsdskgf'] = ''
        self.parameters['pcInfo'] = ''
        self.parameters['typeName'] = ''
        self.parameters['aerererdsdxcxdfgfg'] = ''
        # print(self.state)
        # 认证
        self.authenticate()
        # 刷新用户名
        self.refreshUserName()
        self.getAllCourse()
        # 由于网页是采用gb2313格式的，因此在传送数据之前，需要将utf-8的数据转码成gb2312
        # 选择所有未选择的课程
        self.chooseAllCourse()

    def authenticate(self):
        r = requests.post(self.curl + '/_data/index_login.aspx', data=self.parameters, cookies=self.cookies, headers=self.headers)
        # print(r.headers)
        #print(r.text)

    def passwordEncryption(self,userid, pw, shoolcode):
        # 密码加密
        md5_1 = hashlib.md5(pw.encode('utf-8')).hexdigest()
        text = userid + md5_1[0:30].upper() + shoolcode
        md5_2 = hashlib.md5(text.encode('utf-8')).hexdigest()
        return md5_2[0:30].upper()

    def refreshUserName(self):
        # 获取用户名
        r = requests.get(self.curl + r'/PUB/foot.aspx', cookies=self.cookies, headers=self.headers)
        idandname = self.re_getUserIdName.findall(r.text)[0].split(']')
        uid = idandname[0]
        name = idandname[1]
        if(name):
            self.uname = name
            self.state = self.ONLINE
        # print(self.state)

    def getAllCourse(self):
        # 获取所有主修（本年级/专业）
        r = requests.post(self.curl + r'/wsxk/stu_btx_rpt.aspx', data={'sel_lx':'0', 'SelSpeciality': self.Uid[:4] + '0901'}, cookies=self.cookies)
        # 获取到这次选课的所有的科目
        tableInfo = self.re_getCourseTable.findall(r.text)[0]
        # 解析文档
        tableDom = etree.HTML(tableInfo)
        # 查找信息
        courseItems = tableDom.xpath(r'//tr')[1:-2]
        for item in courseItems:
            cnameandselected = item.xpath(r'.//a')
            infos = item.xpath(r'.//td')
            index = infos[0].text
            cvalue = infos[1].xpath(r"./input")[0].get('value')
            cid = cnameandselected[1].get('value')
            isSelected = cnameandselected[1].text == '查看'
            # print(cvalue)
            self.courses[cnameandselected[0].text] = CourseInfo(curl=self.curl, cname=cnameandselected[0].text, 
                cvalue=cvalue, cid=cid, cselected=isSelected, authenCookies= self.cookies)
            # print(self.courses)

    def chooseAllCourse(self):
        chooseCommand = 'TTT'
        for course in self.courses.values():
            # print(type(course))
            if(not course.isSelected()):
                firstTeacher = course.getTeachers()
                # print(firstTeacher)
                chooseCommand += ',' + firstTeacher[0].getChooseId() + '#' + course.getchkKC()
        # print(chooseCommand)
        chooseCommand = chooseCommand.encode('gb2312')
        self.chooseCourse(chooseCommand)



    def chooseCourse(self, chooseInfo):
        r = requests.post(self.curl + r'/wsxk/stu_btx_rpt.aspx?func=1', data={'id':chooseInfo}, cookies = self.cookies)
        
        # print(r.status_code)


# 课程的信息
class CourseInfo:
    re_gethid_skfs = re.compile(r"hid_skfs'\svalue='[^']+")
    re_getchooseid = re.compile(r"value='\[\d+\][^@]+@\d+@[^']+")

    def __init__(self, curl, cname, cvalue = None, cid=None, ctype=None, cselected=False, cselectedteacher=None, authenCookies = None):
        self.index = 0
        # 选课代码和教师
        self.cteachers = {}
        self.climit = 0
        self.cname = cname
        self.cvalue = cvalue
        self.cselected = cselected
        self.ctype = ctype
        self.cselectedteacher = cselectedteacher
        self.curl = curl
        self.authenCookies = authenCookies
        self.cid = cid
        self.getAllOptionalTeachers()
        # print(self.cteachers)

    def getAllOptionalTeachers(self):
        r = requests.get(self.curl + r'/wsxk/stu_xszx_skbj.aspx?lx=BX&id=' + self.cid + r'&skbjval=', cookies = self.authenCookies)
        # print(self.curl + r'/wsxk/stu_xszx_skbj.aspx?lx=BX&id=' + self.cid + r'&skbjval=')
        hid_skfsInfo = self.re_gethid_skfs.findall(r.text)[0].split("'")[-1]
        nameandchooseid = self.re_getchooseid.findall(r.text)[0].split("'")[-1].split('@'+hid_skfsInfo+'@')
        self.cteachers[nameandchooseid[0]]=Teachers(nameandchooseid[0], nameandchooseid[1])

    def isSelected(self):
        return self.cselected

    def getTeachers(self):
        return list(self.cteachers.values())

    def getchkKC(self):
        return self.cvalue


class Teachers:

    def __init__(self, name, chooseId):
        self.name = name
        self.chooseId = chooseId

    def __str__(self):
        return 'name:' + self.name + ',' + 'chooseId:' + self.chooseId

    def __repr__(self):
        return str(self)

    def getChooseId(self):
        return self.chooseId


if __name__ == '__main__':
    u = User('学号', '密码')