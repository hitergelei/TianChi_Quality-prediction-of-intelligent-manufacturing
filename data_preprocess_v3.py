# -*- coding: utf-8 -*-
"""
Created on Sat Dec 30 15:22:54 2017

v2相比的改进：
1. 消除所有数值完全一样或全部为nan的数据列；
2. 将所有时间的数据转为线性的时间戳；

@author: pengxu
"""

import os, sys, time, logging
import pandas as pd

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

INDEX_ID = 'ID'            

def dataframe_to_excel(data, savepath, name):
    #将数据按照excel保存,需要将INDEX_ID转化保存
    save_path_name = os.path.join(savepath, name+'.xlsx')
    writer = pd.ExcelWriter(save_path_name)
    data.to_excel(writer,'Sheet1')
    writer.save()       
    
def date_to_strptime(data):
    #将所有数据转化为17位的格式%Y%m%d%H%M%S%ms，全部采用补全的方式即可
    use_len = 17
    data_len = int(np.log10(data) + 1)
    use_data = int(data) * (10**(use_len - data_len))
    ms = use_data%1000
    use_transfer_data = str(int(use_data/1000))
    timeArray = time.strptime(use_transfer_data, "%Y%m%d%H%M%S")
    #dt_new = time.strftime("%Y-%m-%d %H:%M:%S",timeArray)
    timestamp = time.mktime(timeArray)
    new_data = timestamp*1000 + ms
    return new_data

class DataPreprocess:
    def __init__(self):
        #日志保存
        log_savepath = r'.'
        log_filename = "record_data_preprocess.log"
        logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename=os.path.join(log_savepath, log_filename),
                        filemode='a')
        #################################################################################################
        #定义一个StreamHandler，将INFO级别或更高的日志信息打印到标准错误，并将其添加到当前的日志处理对象#
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        #formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s') #levelname共占据8个字段
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        #################################################################################################
            
        self.data_directory = r'data'
        self.data_list = ['训练', '测试A', '测试B']
        
        logging.info('read files from %s, the data_preprocess started !!!' % (self.data_directory))
        
    def data_read(self):
        #将所有数据读出
        self.raw_data = {} #保存原始xlsx全部信息
        for data_name in self.data_list:
            data_path = os.path.join(self.data_directory, data_name + '.xlsx')
            df = pd.read_excel(data_path)
            df.index = df[INDEX_ID].tolist() #将ID取消了
            del(df[INDEX_ID])
            df.index.name = INDEX_ID #将index名称获取
            self.raw_data[data_name] = df
            logging.info('%s is read successfully !!!'%(data_name))
        self.new_data = {} #保存全部预处理之后的数据
        for data_name in self.data_list:
            self.new_data[data_name] = np.array(self.raw_data[data_name])
        #将所有X数据合并，方便后续处理
        data0 = self.new_data[self.data_list[0]][:,0:-1] #Y值不处理
        data1 = self.new_data[self.data_list[1]]
        data2 = self.new_data[self.data_list[2]]
        self.raw_array_data = np.vstack((data0, data1, data2)) #合并三个矩阵数据
        logging.info('all data being read successfully !!!')
            
    def ascll_transfer(self):      
        #字符转换ASCLL
        (row, col) = self.raw_array_data.shape
        alpha_index = []
        alpha = []
        for i in range(col):
            v = self.raw_array_data[0,i] #刚好第一行数据都是非nan的
            if not isinstance(v, (np.int64, int, float)): #np.int64和int不同
                alpha_index.append(i)
                alpha.append(v)
        for index in alpha_index:
            for j in range(row):
                self.raw_array_data[j,index] = ord(self.raw_array_data[j,index][0])
        self.new_array_data = np.float64(self.raw_array_data) #将str转化完之后，就可以直接转换
        logging.info('ascll_transfer successfully !!!')
        
    def date_data_transfer(self):
        #将所有date数据（8位：20170804，14位：20170705163823，16位：2017072119260120，排除：14位的“17000000000000”）转换为时间戳
        (row, col) = self.new_array_data.shape
        
        '''#方便后续对比分析查看
        date_value, date_col_index = [], []
        for i in range(col):
                data_value = self.new_array_data[0,i]
                if (not np.isnan(data_value)) and (data_value > 0) and (str(int(data_value))[0:3]=='201'): #1.避免出现nan, 2.所有数据大于0，3.2017年的时间(2016的时间都是有问题的)
                    data_len = int(np.log10(data_value) + 1)
                    if data_len == 14 or data_len == 16 or data_len == 8:
                        date_col_index.append(i)
                        date_value.append(data_value)
        '''
        
        for i in range(col):
            for j in range(row):
                data_value = self.new_array_data[j,i]
                if (not np.isnan(data_value)) and (data_value > 0) and (str(int(data_value))[0:3]=='201'): #1.避免出现nan, 2.所有数据大于0，3.2017年的时间(2016的时间都是有问题的)
                    data_len = int(np.log10(data_value) + 1)
                    if data_len == 14 or data_len == 16 or data_len == 8:
                        if data_value == np.float64(20166616661666.0): #唯一的异常数据
                            self.new_array_data[j,i] = np.nan
                        else:
                            self.new_array_data[j,i] = date_to_strptime(data_value)
                        
        logging.info('date_data_transfer successfully !!!')
        
    def nan_replace(self, mode = 'mean'):
        #将所有nan数据进行填充,第一步：合并所有数据，计算均值或中位数，第二步：对所有原来nan数据进行覆盖
        #将一列全部是nan转为0
        (row, col) = self.new_array_data.shape
        nan_num = np.zeros(col, dtype=np.int32)
        all_nan_index = []
        for i in range(col):
            nan_num[i] = np.isnan(self.new_array_data[:,i]).sum()
            if nan_num[i] == row:
                all_nan_index.append(i)
                self.new_array_data[:,i] = 0 #用0填充
                nan_num[i] = 0 #置换了，所以这里设置为0
        #填充非全部为nan的计算结果
        nan_index = list(np.where(nan_num > 0))[0]
        self.mode = mode
        if mode == 'mean':
            data_replace = np.nanmean(self.new_array_data, axis=0)
        elif mode == 'median':
            data_replace = np.nanmedian(self.new_array_data, axis=0)
        for col_index in nan_index:
            for i in range(row):
                if np.isnan(self.new_array_data[i,col_index]):
                    self.new_array_data[i,col_index] = data_replace[col_index]
                    
        #检查一遍
        if np.isnan(self.new_array_data).sum() != 0:
            logging.error('not all nan data replaced !!!')

        logging.info('nan_replace successfully !!!')
            
    def normalization(self):
        #将上述数据进行归一化
        self.std_zero=[]
        (row, col) = self.new_array_data.shape
        data_mean = np.mean(self.new_array_data, axis=0)
        data_std = np.std(self.new_array_data, axis=0)
        for i in range(col):
            if data_std[i] != 0:
                self.new_array_data[:,i] = (self.new_array_data[:,i] - data_mean[i])/data_std[i]
            else:
                self.new_array_data[:,i] = 0 #将所有相同的数据置为0
                self.std_zero.append(i) #将std为0的数据发现标记出来,后续不保存
        logging.info('normalization successfully !!!')
        
        
    def data_seperate_transfer(self):
        #参数提取
        self.data_index_0 = self.raw_data[self.data_list[0]].index
        self.data_index_1 = self.raw_data[self.data_list[1]].index
        self.data_index_2 = self.raw_data[self.data_list[2]].index
        self.data_parameter = self.raw_data[self.data_list[1]].columns #不能选择0，因为分开保存
        
        self.row0, _ = self.raw_data[self.data_list[0]].shape #不能选择0，因为分开保存
        self.row1, _ = self.raw_data[self.data_list[1]].shape
        self.row2, self.col = self.raw_data[self.data_list[2]].shape
        
        #将合并的数据分割开来
        self.save_array_data = {}
        self.save_array_data[self.data_list[0]] = self.new_array_data[0:self.row0,:]
        self.save_array_data[self.data_list[1]] = self.new_array_data[self.row0:(self.row0+self.row1),:]
        self.save_array_data[self.data_list[2]] = self.new_array_data[(self.row0+self.row1):(self.row0+self.row1+self.row2),:]
        logging.info('data seperated successfully !!!')
        
        #将分开的数据保存为dataframe数据
        self.save_dataframe_data = {}
        self.save_dataframe_data[self.data_list[0]] = pd.DataFrame(self.save_array_data[self.data_list[0]], index = self.data_index_0, columns = self.data_parameter)
        self.save_dataframe_data[self.data_list[1]] = pd.DataFrame(self.save_array_data[self.data_list[1]], index = self.data_index_1, columns = self.data_parameter)
        self.save_dataframe_data[self.data_list[2]] = pd.DataFrame(self.save_array_data[self.data_list[2]], index = self.data_index_2, columns = self.data_parameter)
        
        #删除std为0的数据，没有保存的必要，还增加后续运算的负担
        for col in self.std_zero:
            del(self.save_dataframe_data[self.data_list[0]][self.data_parameter[col]])
            del(self.save_dataframe_data[self.data_list[1]][self.data_parameter[col]])
            del(self.save_dataframe_data[self.data_list[2]][self.data_parameter[col]])
        #单独保存最后一列数据
        self.save_dataframe_data_Y = self.raw_data[self.data_list[0]]['Y'] 
        logging.info('array transfer to dataframe successfully !!!')
                
    def data_save(self):
        #有些过程太漫长，保存中间步骤，避免后续太麻烦
        base_savepath = 'temp_data'
        savepath = os.path.join(base_savepath, self.mode)
        if not os.path.exists(savepath):
            os.makedirs(savepath) #如果目录不存在，makedirs函数会自动创建父目录
        for k,v in self.save_dataframe_data.items():
            dataframe_to_excel(v, savepath, k)
        dataframe_to_excel(self.save_dataframe_data_Y, savepath, 'Y')
        logging.info('data_to_save successfully !!!')
        
def main():
    time_start = time.time()
    
    dp = DataPreprocess()
    dp.data_read() #读“训练.xlsx”数据时间太长
    dp.ascll_transfer() #时间也太长。。。
    dp.date_data_transfer()
    dp.nan_replace(mode='mean') #时间也太长了。。。"median""mean"
    dp.normalization()
    dp.data_seperate_transfer()
    dp.data_save() #时间太长。。。
    
    time_stop = time.time()        
    logging.info('The data_preprocess is finished, all process time is %d s !!!' %(time_stop-time_start))
                  
if __name__ == '__main__':
    main()




















