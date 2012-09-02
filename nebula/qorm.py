#!/usr/bin/python

import sqlite3

class QOrm(object):
    def __init__(self,db,isolation=None):
        self.debug = 1
        self.db = db
        self.tables = {}
        if isolation:
            isolation="DEFERRED"
        self.isolation = isolation
        self.conn = sqlite3.connect(self.db,isolation_level=self.isolation)
        self.cursor = self.conn.cursor()
        self.reload()
    def __getitem__(self,t):
        return self.table(t)
    def close():
        if self.conn:
            self.conn.close()
            self.conn=None
    def reload(self):
        for i in self.query("SELECT name FROM sqlite_master WHERE type='table'"):
            self.tables[i['name']]=i['name']
    def begin(self):
        return self.__class__(self.db,1)
    def commit(self):
        return self.conn.commit()
    def rollback():
        return self.conn.rollback()
    def script(self,sql):
        self.cursor.executescript(sql)
    def lastrowid(self):
        return self.cursor.lastrowid
    def query(self,q,*l,**kw):
        if l:
            if isinstance(l[0],(list, tuple, dict)):
                param = l[0]
            else:
                param = l
        else:
            param = kw
        if self.debug:
            print q,param
        self.cursor.execute(q,param)
        r = []
        for row in self.cursor.fetchall():
            tmp = [(col[0],value) for (col, value) in zip(self.cursor.description, row)]
            r.append(dict(tmp))
        if self.debug:
            print r
        return r
    def table(self,t):
        return QOrmTable(self,t)
    def relation(self,t1,t2):
        l = [t1,t2]
        l.sort()
        return '_'.join(l) # _rel ?

class QOrmSQLite(QOrm):
    pass

class QOrmTable(object):
    def __init__(self,qorm,name):
        self.qorm = qorm
        self.name = name
    def __getitem__(self,k):
        return self.where(id=k).select()[0]
    def insert(self,*l,**kw):
        """ Insert rows in the table
        t.insert(col=val)
        t.insert({col:val})
        t.insert({col:val}, {col:val})
        t.insert([{col:val}, {col:val}])
        """
        l = list(l)
        if kw:
            l.append(kw)
        for d in l:
            if isinstance(d,list):
                self.insert(*d)
            else:
                field, values =  zip(*d.items())
                s1 = ','.join(field)
                s2 = ','.join(['?']*len(d))
                q = "INSERT INTO %s (%s) VALUES (%s)"%(self.name,s1,s2)
                self.qorm.query(q,values)
        return self.qorm.lastrowid()
    def create(self,*l,**kw):
        return self[self.insert(*l,**kw)]
    def where(self,*l,**kw):
        return QOrmWhere(self,*l,**kw)
    def join(self,*l,**kw):
        print self.name,l,kw

class QOrmCondition(list):
    def AND(self,r,op='AND'):
        if not isinstance(r,QOrmCondition):
            return self.AND(QOrmCondition(r))
        if self and r:
            return QOrmCondition([self,'AND',r])
        elif self:
            return self
        else:
            return r
    def OR(self,r):
        return self.AND(r,op='OR')
    def sql(self,e=None):
        if e==None:
            return self.sql(self)
        if e==[] or e==():
            return ("",[])
        else:
            if isinstance(e[0],(list,tuple)):
                (lf,lp)=self.sql(e[0])
            else:
                (lf,lp)=(e[0],[])
            if isinstance(e[2],(list,tuple)):
                (rf,rp)=self.sql(e[2])
            else:
                (rf,rp)=('?',[e[2]])
            return ("(%s %s %s)"%(lf,e[1],rf),lp+rp)

class QOrmWhere(object):
    def __init__(self,table,*l,**kw):
        self.table = table
        self.c = QOrmCondition()
        self.AND(*l,**kw)
    def process_list(self,l,c=None):
        if c==None:
            c=QOrmCondition()
        if l:
            if isinstance(l[0],(list,tuple)):
                return self.process_list(l[1:],self.process_list(l[0],c))
            else:
                return self.process_list(l[3:],c.AND(l[:3]))
        return c
    def process_dict(self,d):
        c = QOrmCondition()
        for k,v in d.items():
            if isinstance(v,list):
                c = c.AND([k,'in',v])
            else:
                c = c.AND([k,'=',v])
        return c
    def AND(self,*l,**kw):
        self.c = self.c.AND(self.process_list(l))
        self.c = self.c.AND(self.process_dict(kw))
        return self
    def OR(self,*l,**kw):
        self.c = self.c.OR(self.process_list(l))
        self.c = self.c.OR(self.process_dict(kw))
        return self
    def NOT(self):
        pass
    def sql(self):
        s,p = self.c.sql()
        if s:
            return ("WHERE %s"%s,p)
        else:
            return ("",[])
    def select(self,limit=None,offset=None):
        s,p = self.sql()
        q = "SELECT * FROM %s %s"%(self.table.name,s)
        if limit:
            q += " LIMIT %s "%limit # or ?
        if offset:
            q += " OFFSET %s "%offset # or ?
        r = self.table.qorm.query(q,p)
        return [QOrmRow(self.table,i) for i in r]
    def delete(self):
        s,p = self.sql()
        q = "DELETE FROM %s %s"%(self.table.name,s)
        return self.table.qorm.query(q,p)
    def update(self,*l,**kw):
        pass

class QOrmRow(dict):
    def __init__(self,table, d):
        self.table = table
        self.dirty = {}
        dict.__init__(self,d)
    def __getitem__(self,k):
        try: 
            return dict.__getitem__(self,k)
        except KeyError,e:
            if dict.__contains__(self, k+'_id'):
                return self.m2o(k+'_id')
            # TODO m2m alphabetic
            elif self.table.qorm.relation(self.table.name,k) in self.table.qorm.tables:
                return self.m2m(k)
            elif k in self.table.qorm.tables:
                return self.o2m(k)
            raise e
    def __getattr__(self,k):
        return self[k]
    def update(self,**d2):
        pass
    def m2o(self,field,table=None):
        if table == None:
            table = field[:-3]
        return self.table.qorm.table(table)[self[field]]
    def o2m(self,table,field=None):
        if field == None:
            field = self.table.name+'_id'
        return self.table.qorm.table(table).where(field,'=',self['id']).select()
    def m2m(self,table,relation=None,field_src=None,field_dest=None):
        if relation==None:
            relation = self.table.qorm.relation(self.table.name,table)
        if field_src == None:
            field_src = self.table.name+'_id'
        if field_dest == None:
            field_dest = table+'_id'
        # TODO use join
        r = self.table.qorm.table(relation).where(field_src,'=',self['id']).select()
        ids = [i[field_dest] for i in r]
        return self.table.qorm.table(table).where(id=ids).select()

def test_init():
    o=QOrm(':memory:')
    o.script("""
BEGIN TRANSACTION;
create table symbol (id integer NOT NULL PRIMARY KEY, symbol text, name text);
create table stocks (id integer NOT NULL PRIMARY KEY, date text, symbol_id integer, trans text, qty real, price real);
insert into symbol values (1,'RHAT','RedHat');
insert into symbol values (2,'MSFT','Microsoft');
insert into stocks values (1,'2006-01-05',1,'BUY',100,35.14);
insert into stocks values (2,'2006-01-05',2,'BUY',100,35.14);
COMMIT;
""")
    o.reload()
    return o

def test_query():
    o = test_init()
    o.query("select * from symbol")
    o.query("select * from symbol where symbol=?",'MSFT')
    o.query("select * from symbol where symbol=?",['MSFT'])
    o.query("select * from symbol where symbol=:s",s='MSFT')
    o.query("select * from symbol where symbol=:s",{"s":'MSFT'})

def test_table_insert():
    o = test_init()
    rid = o.table('symbol').insert(symbol='GOOG',name='Google')
    print rid
    rid = o.table('symbol').insert({'symbol':'GOOG','name':'Google'},{'symbol':'INTL','name':'Intel'})
    print rid
    rid = o.table('symbol').insert([{'symbol':'GOOG','name':'Google'},{'symbol':'INTL','name':'Intel'}])
    print rid
    o.table('symbol').where().select()

def test():
    test_query()
    test_table_insert()
#    print qo.table('stocks').where().select()
#    print qo.table('stocks').where(symbol_id=1,qty=100).sql()
#    print qo.table('stocks').where('symbol_id','=',1,qty=100).sql()
#    print qo.table('stocks').where('symbol_id','=',1,'qty','=',100).sql()
#    r = qo.table('stocks').where([('symbol_id','=',1),('qty','=',100)]).select()
#    for i in r:
#        print i.qty
#        print i.symbol
#        print i.symbol.stocks
#    print qo.table('symbol').create(symbol='a',name='b')
##c.execute("""""")
#    r = qo.table('lottery').where(name="name1","name",'>=',3).AND('amount','>=',1).update({'k':'v'} )
#    r = qo.table('lottery').where(name="name1","name",'>=',3).AND('amount','>=',1).update(k=v)
#    r = qo.table('lottery').where(name="name1","name",'>=',3).AND('amount','>=',1).delete()
#    r = qo.table('lottery').where(name="name1","name",'>=',3).AND('amount','>=',1).select()
#    r = qo.table('lottery')[1] == .where(id="1").AND('amount','>=',1).select()
if __name__ == '__main__':
    test()

