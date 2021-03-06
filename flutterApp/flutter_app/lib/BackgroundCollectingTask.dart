import 'dart:convert';
import 'package:flutter_app/models/audioManager.dart';
import 'package:flutter_app/models/user.dart';
import 'package:flutter_bluetooth_serial/flutter_bluetooth_serial.dart';
import 'package:http/http.dart' as http;
import 'constants.dart' as constants;

class DataSample {
  double heartrate;
  DateTime timestamp;

  DataSample({
    this.heartrate,
    this.timestamp,
  });
}

class BackgroundCollectingTask {
  final BluetoothConnection _connection;
  List<int> _buffer = List<int>();

  // @TODO , Such sample collection in real code should be delegated
  // (via `Stream<DataSample>` preferably) and then saved for later
  // displaying on chart (or even stright prepare for displaying).
  // @TODO ? should be shrinked at some point, endless colleting data would cause memory shortage.
  List samples = [];

  bool inProgress;
  AudioManager audioManager = AudioManager();
  BackgroundCollectingTask._fromConnection(this._connection) {
    _connection.input.listen((data) {
      print('dataa');
      _buffer += data;

  
      while (true) {
        // If there is a sample, and it is full sent
        int index = _buffer.indexOf('t'.codeUnitAt(0));
        var datasample = {};
        if (index >= 0 && _buffer.length - index >= 2) {
          datasample["heartrate"] = (_buffer[index + 1] );
          datasample["timestamp"] = DateTime.now().toString();
          _addSample(datasample);

          _buffer.removeRange(0, index + 2);
        }
        // Otherwise break
        else {
          break;
        }
      }
    }).onDone(() {
      inProgress = false;
    });
  }

  static Future<BackgroundCollectingTask> connect(
      BluetoothDevice server) async {
    final BluetoothConnection connection =
        await BluetoothConnection.toAddress(server.address);
    return BackgroundCollectingTask._fromConnection(connection);
  }

  void dispose() {
    _connection.dispose();
  }

  Future<void> start() async {
    inProgress = true;
    _buffer.clear();
    samples.clear();

    _connection.output.add(ascii.encode('start'));
    await _connection.output.allSent;
    print("started");
  }

  Future<void> cancel() async {
    inProgress = false;

    _connection.output.add(ascii.encode('stop'));
    await _connection.finish();
  }

  Future<void> pause() async {
    inProgress = false;

    _connection.output.add(ascii.encode('stop'));
    await _connection.output.allSent;
  }

  Future<void> reasume() async {
    inProgress = true;

    _connection.output.add(ascii.encode('start'));
    await _connection.output.allSent;
  }

  Iterable<DataSample> getLastOf(Duration duration) {
    DateTime startingTime = DateTime.now().subtract(duration);
    int i = samples.length;
    do {
      i -= 1;
      if (i <= 0) {
        break;
      }
    } while (samples[i].timestamp.isAfter(startingTime));
    return samples.getRange(i, samples.length);
  }

  void _addSample(Map datasample) {
    samples.add(datasample);
    if (samples.length >= 4) {
      _sendToServer();
      samples = [];
    }
  }

  void _sendToServer() async{
    var user = User();
    var total = 0;
    for(int i = 0; i < this.samples.length; i++){
      total += this.samples[i]['heartrate'];
    }
    int avg = (total / this.samples.length).floor() ;
    var time = DateTime.now().toString();
    var data = json.encode(
      {
        "uid": user.uid,
        "data": [{"timestamp" : time, "heartrate": avg}]
      }
  );
    var response = await http.post(constants.URL + "/sleepdata", body:data);
    if(response.statusCode == 200){
      var responseData = json.decode(response.body);
      if(responseData["wakeup"]){
        audioManager.play();
      }
    }
  }
}
