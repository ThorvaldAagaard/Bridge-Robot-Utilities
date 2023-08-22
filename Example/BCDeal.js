// This script file is licensed under a Creative Commons
// Attribution 4.0 International License (cc by 4.0):
// http://creativecommons.org/licenses/by/4.0/
// You may adapt and/or share this script file for any purpose,
// provided you give credit to http://bridgecomposer.com
//
//  This "includable" script implements a Deal object.
//  The Deal object breaks down a PBN 'Deal' tag value.
//  It has a 'hand' array of four objects (for North, East, South, and West),
//  each with a 'suit' array of four objects (for Spades, Hearts, Diamonds, and Clubs).
//
//  Each suit object has properties and function:
//    length                // number of cards in suit
//    hcp                   // high card points in suit
//    hasCard(iRank)        // rank number as defined below

//  Each hand object has properties and functions:
//    hcp                   // high card points in hand
//    isBalanced(bSemi)     // bSemi is optional: "true" for semi-balanced
//    hasCard(card)         // card is a string of two char: suit + rank, e.g. "SK"
//    hasCard(suit, rank)   // suit and rank numbers as defined below
//    hasCard2(suit, rank)  // (same as hasCard(suit rank))
//    longest()             // longest suit (highest ranking, if ties)
//
//    $Id: BCDeal.js 109 2022-09-03 04:06:15Z Ray $

// The following are constants (used to help clarify code):
var NORTH = 0, EAST = 1, SOUTH = 2, WEST = 3, NHANDS = 4;
var SPADES = 0, HEARTS = 1, DIAMS = 2, CLUBS = 3, NSUITS = 4;
var RANK_2 = 2, RANK_3 = 3, RANK_4 = 4, RANK_5 = 5, RANK_6 = 6;
var RANK_7 = 7, RANK_8 = 8, RANK_9 = 9, RANK_10 = 10;
var RANK_J = 11, RANK_Q = 12, RANK_K = 13, RANK_A = 14;

var deal_strHand = 'NESW';
var deal_strSuit = 'SHDC';
var deal_strSuitName = ['spade', 'heart', 'diamond', 'club'];
var deal_strRank = '23456789TJQKA';

function Suit() {
  this.card = 0;
  this.length = 0;
  this.hcp = 0;
}

Suit.prototype.hasCard = function(iRank) {
  return (this.card & (1 << iRank)) !== 0;
}

function Hand() {
  this.hcp = 0;
  this.suit = [];
  for (var iSuit = 0; iSuit < NSUITS; ++iSuit)
    this.suit[iSuit] = new Suit;
}

Hand.prototype.hasCard = function(arg1, arg2) {
  if (arguments.length >= 2)
    return this.hasCard2(arg1, arg2);

  var strCard = arg1.toUpperCase();
  var iSuit = deal_strSuit.indexOf(strCard.charAt(0));
  var ch = strCard.charAt(1);
  var iRank = deal_strRank.indexOf(ch) + RANK_2;
  return this.hasCard2(iSuit, iRank);
}

Hand.prototype.hasCard2 = function(iSuit, iRank) {
  return this.suit[iSuit].hasCard(iRank);
}

Hand.prototype.isBalanced = function(bSemi) {
// Optional argument "bSemi": specify "true" to include semi-balanced
  var c2 = 0;
  var c2max = (bSemi) ? 2 : 1;
  for (var iSuit = 0; iSuit < NSUITS; ++iSuit) {
    switch (this.suit[iSuit].length) {
      case 2:
        if (++c2 > c2max) return false;
        break;
      case 3:
      case 4:
      case 5:
        break;
      default:
        return false;
    }
  }
  return true;
}

Hand.prototype.longest = function() {
  var iLongest = -1;
  var cLongest = -1;
  for (var iSuit = 0; iSuit < NSUITS; ++iSuit) {
    var len = this.suit[iSuit].length;
    if (len > cLongest) {
      iLongest = iSuit;
      cLongest = len;
    }
  }
  return iLongest;
}

function Deal(strDeal) {
  strDeal = strDeal.toUpperCase();
  this.hand = [];
  for (var iHand = 0; iHand < NHANDS; ++iHand)
    this.hand[iHand] = new Hand;
  var ch = strDeal.charAt(0);
  var iHand = deal_strHand.indexOf(ch);
  var iSuit = 0;
  for (var iChar = 2, len = strDeal.length; iChar < len; ++iChar) {
    ch = strDeal.charAt(iChar);
    if (ch === '.') {
      ++iSuit;
    } else if (ch === ' ') {
      iHand = (iHand + 1) & 3;
      iSuit = 0;
    } else {
      var h = this.hand[iHand];
      var s = h.suit[iSuit];
      var r = deal_strRank.indexOf(ch) + RANK_2;
      s.card |= (1 << r);
      ++s.length;
      if (r >= RANK_J) {
        var ncp = r - RANK_J + 1;
        s.hcp += ncp;
        h.hcp += ncp;
      }
    }
  }
}

Deal.prototype.format = function(strDealer) {
  // We format the deal with dealer's hand first (PBN standard order)
  strDealer = strDealer.toUpperCase();
  var iHand = deal_strHand.indexOf(strDealer);
  if (iHand < 0 || strDealer.length !== 1)
    throw new Error('Deal.format: invalid dealer');
  var strDeal = strDealer + ':';
  for (var xHand = 0; xHand < NHANDS; ++xHand) {
    for (var iSuit = 0; iSuit < NSUITS; ++iSuit) {
      for (var iRank = RANK_A; iRank >= RANK_2; --iRank) {
        if (this.hand[iHand].suit[iSuit].card & (1 << iRank))
          strDeal += deal_strRank.charAt(iRank - RANK_2);
      }
      if (iSuit < 3) strDeal += '.';
    }
    if (xHand < 3) strDeal += ' ';
    iHand = (iHand + 1) & 3;
  }
  return strDeal;
}
