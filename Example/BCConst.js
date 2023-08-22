// This script file is licensed under a Creative Commons
// Attribution 4.0 International License (cc by 4.0):
// http://creativecommons.org/licenses/by/4.0/
// You may adapt and/or share this script file for any purpose,
// provided you give credit to http://bridgecomposer.com
//
//  This "includable" script declares constants used in
//  BridgeComposer object method calls.
//
//  $Id: BCConst.js 121 2022-11-17 16:44:07Z Ray $

//  Message box options, used in the "type" parameter to the
//  BC object "alert", "confirm", and "prompt" methods:

//  Message box severity

var MB_ICONINFORMATION = 64;
var MB_ICONWARNING = 48, MB_ICONEXCLAMATION = 48; // (synonyms)
var MB_ICONERROR = 16, MB_ICONSTOP = 16; // (synonyms)

//  Message box button labels ("confirm" only)

var MB_YESNO = 4;
var MB_RETRYCANCEL = 5;

//  Message box default button (for "confirm" and "prompt" only)

var MB_DEFBUTTON2 = 256;

//  Operation codes used for the first parameter to the
//  BC object "progress" method:

var BCP_UPDATE = 0; // update progress
var BCP_TITLE = 1;  // set progress panel title
var BCP_CLOSE = 2;  // close progress panel
var BCP_BUTTON = 3; // set button label
var BCP_FINISH = 4; // change to "alert" box with Close button

//  "section" parameter values for the Board object "Commentary" property:

var CMTY_EVENT = 0;
var CMTY_DIAGRAM = 1;
var CMTY_AUCTION = 2;
var CMTY_FINAL = 3;

//  "type" parameter values for the Board object "WriteImageFile" method:

var IMAGE_PNG = 1;
var IMAGE_BMP = 2;
var IMAGE_JPEG = 3;
var IMAGE_EMF = 4;

//  "flags" parameter values (to be summed) for the Board object "WriteImageFile" method:

var WIFF_CLEARTYPE = 1;
var WIFF_PAGE = 2;


//  BridgeComposer access with minimum version check

function GetBC(minver)
{
  if (minver) {
    if (typeof minver !== 'string')
      throw 'GetBC argument must be a string, because trailing zeros are significant'
  } else {
    minver = '5.61';  // default if "minver" omitted
  }
  
  try {
    var bc = WScript.CreateObject('BridgeComposer.Object');
  } catch (e) {
    WScript.Echo('To run this script, you need to install BridgeComposer ' +
      '(version ' + minver + ' or later).\r\n\r\n' +
      'Visit https://bridgecomposer.com and click "Download Now".');
    WScript.Quit(1);
  }
  
  var arrMin = minver.split('.');
  while (arrMin.length < 3)
    arrMin.push(0);
  
  var arrNow = bc.Version.split('.');
  while (arrNow.length < 3)
    arrNow.push(0);
  
  for (var i = 0; i < 3; ++i) {
    arrMin[i] = parseInt(arrMin[i]);
    arrNow[i] = parseInt(arrNow[i]);
    if (arrNow[i] > arrMin[i])
      break;
    
    if (arrNow[i] < arrMin[i]) {
      WScript.Echo('To run this script, you need to update BridgeComposer ' +
        'to version ' + minver + ' or later.\n\n' +
        'In BridgeComposer, use the "Help>Check For Updates" menu command.');
      WScript.Quit(1);
    }
  }
  
  return bc;
}
