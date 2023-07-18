from collections import namedtuple
from django.db.models import Q
from functools import reduce
import operator,json

order_dict = {'asc': '', 'desc': '-'}


class DataTablesServer(object):
    def __init__(self, datatable, columns, qs, searchField,request, serializer=None):
        self.columns = columns
        # values specified by the datatable for filtering, sorting, paging        
        self.request_values = datatable
        # serializerField
        self.serializer = serializer
        
        # For building image
        self.request = request
        
        # searchtxt
        self.searchField = searchField
        # results from the db
        self.result_data = None
        # total in the table after filtering
        self.cardinality_filtered = 0
        # total in the table unfiltered
        self.cardinality = 0
        # self.user = request.user
        self.qs = qs
        self.run_queries()

    def output_result(self):
        output = dict()
        
        output['recordsTotal'] = str(self.data_length)
        output['recordsFiltered'] = str(self.cardinality_filtered)
        output['aaData'] = self.result_data
        return output

    def run_queries(self):
        # pages has 'start' and 'length' attributes
        pages = self.paging()
        # the term you entered into the datatable search
        _filter = self.filtering()
        # the document field you chose to sort
        sorting = self.sorting()
        # custom filter
        qs = self.qs

        if _filter:
            # get your filtered data
           
            queryset = qs.filter(reduce(operator.or_, _filter)).order_by('%s' % sorting)
            if self.serializer:
                serializer_class=self.serializer(queryset ,many=True,context={'request':self.request}).data
                len_data = len(serializer_class)
                self.data_length = len_data
                data = serializer_class[pages.start:pages.length]
            else:
                # data = qs.filter(reduce(operator.or_, _filter)).order_by('%s' % sorting)
                len_data = len(queryset)
                self.data_length = len_data
                data = list(queryset.values(*self.columns)[pages.start:pages.length])
        else:
           
            if self.serializer:
                data=self.serializer(qs.order_by('%s' % sorting),many=True,context={'request':self.request}).data
     
            else:
                data = qs.order_by('%s' % sorting).values(*self.columns)
            
            len_data =len(data)
            _index = int(pages.start)
            self.data_length = len_data
            data = data[_index:_index + (pages.length - pages.start)]

        self.result_data = list(data)

        # length of filtered set
        if _filter:
            self.cardinality_filtered = len_data
        else:
            self.cardinality_filtered = len_data
        self.cardinality = pages.length - pages.start
        
    def filtering(self):
        # build your filter spec
        or_filter = []
        if (self.request_values.get('search[value]')[0]) and (self.request_values.get('search[value]')[0] != ""):
            if '/' in self.request_values.get('search[value]')[0]:
                date = ''.join(self.request_values.get('search[value]')[0]).split('/')
                if len(date) == 2:
                    db_dateformat = '-' +date[0]

                elif len(date) >= 2:
                    db_dateformat = '-' + date[1] + '-' + date[0]
     
                elif len(date) > 2:    
                    db_dateformat = date[2] + '-' + date[1] + '-' + date[0]
               
                self.request_values.get('search[value]')[0] = db_dateformat
            for i in range(len(self.searchField)):
                or_filter.append((self.searchField[i]+'__icontains', self.request_values.get('search[value]')[0]))
            
        q_list = [Q(x) for x in or_filter]
        return q_list

    def sorting(self):
      
        # column number
        if self.request_values.get('order[0][column]') != None:
            column_number = int(self.request_values.get('order[0][column]')[0])    
        else:
            column_number = 0 
        # sort direction
        if self.request_values.get('order[0][dir]') != None:
            sort_direction = self.request_values.get('order[0][dir]')[0]
        else:
            
            sort_direction ='desc' 

        order = order_dict[sort_direction]+self.columns[column_number]        
        return order

    def paging(self):
        
        pages = namedtuple('pages', ['start', 'length'])

        if (self.request_values.get('start')[0] != "") and (self.request_values.get('length')[0] != -1):
            pages.start = int(self.request_values.get('start')[0])
            if int(self.request_values.get('length')[0]) == -1:
                pages.length = pages.start + int(len(self.qs))
            else:
                pages.length = pages.start + int(self.request_values.get('length')[0])
        return pages