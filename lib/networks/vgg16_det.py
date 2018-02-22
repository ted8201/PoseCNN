import tensorflow as tf
from networks.network import Network

class vgg16_det(Network):
    def __init__(self, input_format, num_classes, feature_stride, anchor_scales=(8, 16, 32), anchor_ratios=(0.5, 1, 2), trainable=True, is_train=True):
        self.inputs = []
        self.input_format = input_format
        self.num_classes = num_classes
        self.feature_stride = feature_stride
        self.anchor_scales = anchor_scales
        self.num_scales = len(anchor_scales)
        self.anchor_ratios = anchor_ratios
        self.num_ratios = len(anchor_ratios)
        self.num_anchors = self.num_scales * self.num_ratios
        if is_train:
            self.is_train = 1
        else:
            self.is_train = 0

        self.data = tf.placeholder(tf.float32, shape=[None, None, None, 3])
        if input_format == 'RGBD':
            self.data_p = tf.placeholder(tf.float32, shape=[None, None, None, 3])
        self.im_info = tf.placeholder(tf.float32, shape=[3])
        self.gt_boxes = tf.placeholder(tf.float32, shape=[None, 5])
        self.keep_prob = tf.placeholder(tf.float32)

        # define a queue
        queue_size = 25
        if input_format == 'RGBD':
            q = tf.FIFOQueue(queue_size, [tf.float32, tf.float32, tf.float32, tf.float32, tf.float32])
            self.enqueue_op = q.enqueue([self.data, self.data_p, self.im_info, self.gt_boxes, self.keep_prob])
            data, data_p, im_info, gt_boxes, self.keep_prob_queue = q.dequeue()
            self.layers = dict({'data': data, 'data_p': data_p, 'im_info': im_info, 'gt_boxes': gt_boxes})
        else:
            q = tf.FIFOQueue(queue_size, [tf.float32, tf.float32, tf.float32, tf.float32])
            self.enqueue_op = q.enqueue([self.data, self.im_info, self.gt_boxes, self.keep_prob])
            data, im_info, gt_boxes, self.keep_prob_queue = q.dequeue()
            self.layers = dict({'data': data, 'im_info': im_info, 'gt_boxes': gt_boxes})
        self.close_queue_op = q.close(cancel_pending_enqueues=True)

        self.trainable = trainable
        self.setup()

    def setup(self):
        (self.feed('data')
             .conv(3, 3, 64, 1, 1, name='conv1_1', c_i=3)
             .conv(3, 3, 64, 1, 1, name='conv1_2', c_i=64)
             .max_pool(2, 2, 2, 2, name='pool1')
             .conv(3, 3, 128, 1, 1, name='conv2_1', c_i=64)
             .conv(3, 3, 128, 1, 1, name='conv2_2', c_i=128)
             .max_pool(2, 2, 2, 2, name='pool2')
             .conv(3, 3, 256, 1, 1, name='conv3_1', c_i=128)
             .conv(3, 3, 256, 1, 1, name='conv3_2', c_i=256)
             .conv(3, 3, 256, 1, 1, name='conv3_3', c_i=256)
             .max_pool(2, 2, 2, 2, name='pool3')
             .conv(3, 3, 512, 1, 1, name='conv4_1', c_i=256)
             .conv(3, 3, 512, 1, 1, name='conv4_2', c_i=512)
             .conv(3, 3, 512, 1, 1, name='conv4_3', c_i=512)
             .max_pool(2, 2, 2, 2, name='pool4')
             .conv(3, 3, 512, 1, 1, name='conv5_1', c_i=512)
             .conv(3, 3, 512, 1, 1, name='conv5_2', c_i=512)
             .conv(3, 3, 512, 1, 1, name='conv5_3', c_i=512))

        if self.input_format == 'RGBD':
            (self.feed('data_p')
                 .conv(3, 3, 64, 1, 1, name='conv1_1_p', c_i=3)
                 .conv(3, 3, 64, 1, 1, name='conv1_2_p', c_i=64)
                 .max_pool(2, 2, 2, 2, name='pool1_p')
                 .conv(3, 3, 128, 1, 1, name='conv2_1_p', c_i=64)
                 .conv(3, 3, 128, 1, 1, name='conv2_2_p', c_i=128)
                 .max_pool(2, 2, 2, 2, name='pool2_p')
                 .conv(3, 3, 256, 1, 1, name='conv3_1_p', c_i=128)
                 .conv(3, 3, 256, 1, 1, name='conv3_2_p', c_i=256)
                 .conv(3, 3, 256, 1, 1, name='conv3_3_p', c_i=256)
                 .max_pool(2, 2, 2, 2, name='pool3_p')
                 .conv(3, 3, 512, 1, 1, name='conv4_1_p', c_i=256)
                 .conv(3, 3, 512, 1, 1, name='conv4_2_p', c_i=512)
                 .conv(3, 3, 512, 1, 1, name='conv4_3_p', c_i=512)
                 .max_pool(2, 2, 2, 2, name='pool4_p')
                 .conv(3, 3, 512, 1, 1, name='conv5_1_p', c_i=512)
                 .conv(3, 3, 512, 1, 1, name='conv5_2_p', c_i=512)
                 .conv(3, 3, 512, 1, 1, name='conv5_3_p', c_i=512))

            (self.feed('conv5_3', 'conv5_3_p')
                 .concat(3, name='concat_conv5')
                 .conv(3, 3, 512, 1, 1, name='conv_rpn', c_i=1024))
        else:
            (self.feed('conv5_3')
                 .conv(3, 3, 512, 1, 1, name='conv_rpn', c_i=512))

        (self.feed('conv_rpn')
             .conv(1, 1, self.num_anchors * 2, 1, 1, name='rpn_cls_score', c_i=512)
             .reshape_score(2, name='rpn_cls_score_reshape')
             .softmax_high_dimension(2, name='rpn_cls_prob_reshape')
             .reshape_score(self.num_anchors * 2, name='rpn_cls_prob'))

        (self.feed('conv_rpn')
             .conv(1, 1, self.num_anchors * 4, 1, 1, name='rpn_bbox_pred', c_i=512))

        # compute anchors
        (self.feed('im_info')
             .compute_anchors(self.feature_stride, self.anchor_scales, self.anchor_ratios, name='anchors'))

        # compute rpn targets
        (self.feed('rpn_cls_score', 'gt_boxes', 'im_info', 'anchors')
             .compute_anchor_targets(self.num_anchors, name='anchor_targets'))

        self.layers['rpn_labels'] = self.get_output('anchor_targets')[0]
        self.layers['rpn_bbox_targets'] = self.get_output('anchor_targets')[1]
        self.layers['rpn_bbox_inside_weights'] = self.get_output('anchor_targets')[2]
        self.layers['rpn_bbox_outside_weights'] = self.get_output('anchor_targets')[3]

        # compute region proposals
        (self.feed('rpn_cls_prob', 'rpn_bbox_pred', 'im_info', 'anchors')
             .compute_proposals(self.feature_stride, self.num_anchors, 'TEST', name='proposals'))

        self.layers['rois'] = self.get_output('proposals')[0]
        self.layers['rpn_scores'] = self.get_output('proposals')[1]
