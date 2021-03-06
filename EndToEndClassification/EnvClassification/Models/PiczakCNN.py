# Copyright 2018 Corti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tensorflow as tf
import tensorflow.contrib.slim as slim
from tensorflow.contrib.layers.python.layers import initializers
from tensorflow.python.ops import init_ops


class Piczak():
    """
    Baseline convolutional neural network model introduced by Piczak for environmental sound classification using
    logscaled Mel-spectrograms as input.

    For details, see:
    K. J. Piczak. Environmental Sound Classification with Convolutional Neural Networks. In Proceedings of the IEEE
    25th International Workshop on Machine Learning for Signal Processing (MLSP), pp. 1-6, IEEE, 2015.
    """

    def __init__(self, model_name, num_classes=50, weights_initializer=initializers.xavier_initializer(),
                 biases_initializer=init_ops.zeros_initializer(), weights_regularizer=None, biases_regularizer=None):
        """
        Initializes the PiczakCNN model class.

        Args:
            model_name (str): model name.
            num_classes (int): number of the classes (i.e. size of the output layer of the classifier).
            weights_initializer (func): how to initialize the weights of all layers.
            biases_initializer (func): how to initialize the biases of all layers.
            weights_regularizer (func): regularization of the weights of all layers.
            biases_regularizer (func): regularization of the biases of all layers.
        """

        self.model_name = model_name
        self.num_classes = num_classes
        self.W_init = weights_initializer
        self.b_init = biases_initializer
        self.W_reg = weights_regularizer
        self.b_reg = biases_regularizer

    def build_predict_op(self, input_tensor, is_training=False):
        with tf.variable_scope('piczak'):
            predict_op = input_tensor

            # first convolutional block with dropout and with max pooling
            predict_op = slim.convolution(predict_op, 80, [57, 6], stride=[1, 1], padding='VALID',
                                          activation_fn=None,
                                          weights_initializer=self.W_init, biases_initializer=self.b_init,
                                          weights_regularizer=self.W_reg, biases_regularizer=self.b_reg,
                                          scope='cnn_1')
            predict_op = tf.nn.relu(predict_op)
            predict_op = slim.dropout(predict_op, keep_prob=0.5, is_training=is_training, scope='cnn_1')
            predict_op = slim.pool(predict_op, [4, 3], 'MAX', padding='VALID', stride=[1, 3])

            # second convolutional block without dropout (following Piczak) and with max pooling
            predict_op = slim.convolution(predict_op, 80, [1, 3], stride=[1, 1], padding='VALID',
                                          activation_fn=None,
                                          weights_initializer=self.W_init, biases_initializer=self.b_init,
                                          weights_regularizer=self.W_reg, biases_regularizer=self.b_reg,
                                          scope='cnn_2')
            predict_op = tf.nn.relu(predict_op)
            predict_op = slim.pool(predict_op, [1, 3], 'MAX', padding='VALID', stride=[1, 3])

            # reshaping before the dense layers
            predict_op = tf.transpose(predict_op, [0, 2, 1, 3])

            print('shape of output after reshaping')
            # print('should be: bs, 10, 1, num_filters=80')
            print(predict_op.get_shape())

            shx = predict_op.get_shape()
            predict_op = tf.reshape(predict_op, [-1, int(shx[1]), int(shx[2] * shx[3])])
            print('shape of output after reshaping')
            # print('should be: bs, 10, 80')
            print(predict_op.get_shape())

            shx = predict_op.get_shape()
            predict_op = tf.reshape(predict_op, [-1, int(shx[1]) * int(shx[2])])
            print('shape of output after another reshaping')
            # print('should be: bs, 800')
            print(predict_op.get_shape())

            # dense part of the model with dropout
            predict_op = slim.fully_connected(predict_op, 5000, activation_fn=None,
                                              weights_initializer=self.W_init, biases_initializer=self.b_init,
                                              weights_regularizer=self.W_reg, biases_regularizer=self.b_reg,
                                              scope='dense_1')
            predict_op = tf.nn.relu(predict_op)
            predict_op = slim.dropout(predict_op, keep_prob=0.5, is_training=is_training, scope='dense_1')

            predict_op = slim.fully_connected(predict_op, 5000, activation_fn=None,
                                              weights_initializer=self.W_init, biases_initializer=self.b_init,
                                              weights_regularizer=self.W_reg, biases_regularizer=self.b_reg,
                                              scope='dense_2')
            predict_op = tf.nn.relu(predict_op)
            predict_op = slim.dropout(predict_op, keep_prob=0.5, is_training=is_training, scope='dense_2')

            # linear output layer
            predict_op = slim.fully_connected(predict_op, self.num_classes, activation_fn=None,
                                              weights_initializer=self.W_init, biases_initializer=self.b_init,
                                              weights_regularizer=self.W_reg, biases_regularizer=self.b_reg,
                                              scope='output')

        return predict_op

    def get_loss_op(self, prediction, label_tensor):
        """
        Builds the cross entropy loss op.

        Args:
            prediction (tf tensor): model prediction with dimensions [batch_size, num_classes].
            label_tensor (tf tensor): integer labels (not one-hot encoded!) with dimension [batch_size] where
                                    each entry in labels must be an index in [0, num_classes).

        Returns:
            (tf operation): computes cross entropy loss op averaged over the mini-batch.
        """

        loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=label_tensor, logits=prediction)
        loss = tf.reduce_mean(loss)

        return loss

    def save(self, path, sess):
        """
        Saves the model variables to the specified path.

        Args:
            path (str): folder path where the checkpoint will be saved.
            sess (tf Session): the session.
        """

        vars = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope="model")
        saver = tf.train.Saver(vars)
        saver.save(sess, path)

    def load_piczak(self, path, sess):
        """
        Loads the model variables from the specified path.

        Args:
            path (str): folder path from where the checkpoint will be loaded.
            sess (tf Session): the session.
        """

        vars = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope="model")
        saver = tf.train.Saver(vars)
        saver.restore(sess, path)
