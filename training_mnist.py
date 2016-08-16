# -*- coding: utf-8 -*-
from keras.models import Model
from keras.layers import Input
from keras.callbacks import EarlyStopping, LearningRateScheduler
import tensorflow as tf
from vae_m1m2 import VAEM1M2
import os.path
from sklearn.cross_validation import train_test_split
from sklearn.datasets import fetch_mldata
import numpy as np
import cv2

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_boolean('rotation', True, 'use rotate dataset?')
rotation = 'rot' if FLAGS.rotation else 'normal'
print "start {}".format(rotation)

y_dim = 11 if FLAGS.rotation else 10
nb_epoch = 20
batch_size = 100
alpha = 1
learning_rate = 0.01

def get_rotation():
    
    mnist = fetch_mldata('MNIST original')
    X, y = mnist.data, mnist.target.astype(np.int32)
    X = X/255.0
    y = np.eye(np.max(y)+1)[y]

    img    = X[0].reshape(-1, 28)
    center = (img.shape[0]*0.5, img.shape[1]*0.5)
    size   = (img.shape[0], img.shape[1])
    scale  = 1.0

    y = np.concatenate((y, np.zeros(shape=(y.shape[0], 1))), axis=1)
    length = X.shape[0]

    for i, x in enumerate(X):
        print i
        x = x.reshape(-1, 28)
        angle = np.random.randint(0, 180)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)
        x_rot = cv2.warpAffine(x, rotation_matrix, size)
        x_rot = x_rot.reshape(784)
        X[i] = x_rot
        y[i, 10] = angle/180.0

    return X, y

def get_data():
    if FLAGS.rotation:
        if os.path.exists('./data/rotation.npz'):
            data = np.load('./data/rotation.npz')
            X_data = data['x']
            y_data = data['y']
        else:
            X_data, y_data = get_rotation()
            np.savez('./data/rotation.npz', x=X_data, y=y_data)
    else:
        mnist = fetch_mldata('MNIST original')
        X_data, y_data = mnist.data, mnist.target.astype(np.int32)
        X_data = X_data/255.0
        y_data = np.eye(np.max(y_data)+1)[y_data]
    return X_data, y_data

def scheduler(epoch):
    if epoch%5 == 0:
        global learning_rate
        learning_rate = learning_rate*0.1
        return learning_rate
    else:
        return learning_rate


if __name__ == '__main__':
    X_data, y_data = get_data()
    X_train, X_test, y_train, y_test = train_test_split(X_data, y_data, test_size=0.2)

    vaem1m2 = VAEM1M2(y_dim=y_dim, alpha=alpha)
    traininigModel = Model(input=[vaem1m2.x, vaem1m2.y], output=vaem1m2.x_reconstruct)
    traininigModel.compile(optimizer='rmsprop', loss=vaem1m2.loss_function)


    traininigModel.fit([X_train, y_train], X_train,
                        shuffle=True,
                        nb_epoch=nb_epoch,
                        batch_size=batch_size,
                        validation_data=([X_test, y_test], X_test),
                        callbacks=[EarlyStopping(patience=3), LearningRateScheduler(scheduler)])

    # encode to mean deterministic
    encoder = Model(input=[vaem1m2.x, vaem1m2.y], output=vaem1m2.mean)
    encoder.save("./trained_model/encoder_{}.h5".format(rotation))

    decoder_input = Input((vaem1m2.z_dim, ))
    decoder_output = vaem1m2.decoder([vaem1m2.y, decoder_input])
    decoder = Model(input=[vaem1m2.y, decoder_input], output=decoder_output)
    decoder.save("./trained_model/decoder_{}.h5".format(rotation))

