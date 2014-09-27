
import tornado.ioloop
import tornado.web 


class SimpleHandler(tornado.web.RequestHandler): 
    def get(self): 
        self.render('idle.html') 

handlers = [(r'/', SimpleHandler)]

settings = {'template_path': 'templates', 'static_path': 'static'} 

application = tornado.web.Application(handlers, **settings) 
application.listen(8080) 

tornado.ioloop.IOLoop.instance().start() 


