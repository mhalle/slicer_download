var sqlite3 = require('sqlite3');
var async = require('async');
var _ = require('lodash');
var fs = require('fs');

var countries = require('./lib/countries');
var formatVersion = require('./format-version');

var EUCountryInfo = ['European Union', 'Western Europe', 'Europe'];

var BitTable = {
    'i386': 32,
    'amd64': 64
};

// bitstream[id] = {
//     os: {mac,win,linux}
//     arch: {amd64,i386}
//     bits: {32,64} as integers
//     version: (e.g., "4.1.0")
//     stable: {0,1}
//     checkout: (date time)
// }


//
// countryCodeData[countryCode] = [country_name, country_subregion, country_region]
//
//

//
// access = [
//   [bitstreamId, access_date+time, country_code, locationIndex]
//   ...
// ]
//
// location[locationIndex] = locationCoords
//

var CountryCodeQuery = 'select distinct country_code, country_name ' +
'from ipinfo order by country_code';

var BitstreamQuery = 'select * from bsinfo order by bitstream_id';

var AccessQuery = "select " +
"bsinfo.bitstream_id, ipinfo.country_code, " +
"ipinfo.latitude, ipinfo.longitude, " +
"access.ts " +
"from access " +
"join bsinfo on access.bitstream_id = bsinfo.bitstream_id " +
"join ipinfo on access.ip = ipinfo.ip " +
"join uainfo on access.useragent = uainfo.useragent " +
"where uainfo.browser_type = 'Browser' " +
"group by access.ip,bsinfo.bitstream_id " +
"order by access.ts";

main();

function main() {
    var dbfilename = process.argv[2];
    var jsonFilename = process.argv[3];

    var db = new sqlite3.Database(dbfilename);
    async.parallel({
        countryCode: function(callback) {
            processCountryCodeTable(db, callback);
        },
        bitstream: function(callback) {
            processBitstreamTable(db, callback);
        },
        access: function(callback) {
            processAccessTable(db, callback);
        }
    },
    function(err, result) {
        if(err) {
            console.log(err);
        }
        else {
            result.location = result.access.location;
            result.access = result.access.access;
            result._formatVersion = formatVersion;
            var jsoned = JSON.stringify(result);
            fs.writeFile(jsonFilename, jsoned, function(err) {
                if(err) {
                    console.log(err);
                }
            });
        }
    });
}


function processBitstreamTable(db, callback) {
    var versionRE = new RegExp(/^\w*-([0-9.\w]*)(?:-|$)/);
    var table = {};
    db.each(BitstreamQuery, function(err, row) {
        if(!err) {
            var bitstreamId = parseInt(row.bitstream_id);
            var name = row.filename;
            var match = name.match(versionRE);
            var version;
            if(match) {
                version = match[1].split('.').slice(0, 3).join('.');
            }
            else {
                version = '';
            }
            var checkout = row.checkout_date;
            var creation = row.date_creation;
            table[bitstreamId] = {
                os: row.os,
                arch: row.arch,
                bits: BitTable[row.arch],
                version: version,
                stable: row.release === '' ? 0 : 1,
                checkout: checkout ? checkout : creation ? creation : ''
            }
        }
    },
    function(err, nrows) {
        callback(err, table);
    });
}

function processAccessTable(db, callback) {
    var ret = [];
    var locationCache = [];
    var locationLookup = {};
    var locationId = 0;
    var loci;

    db.each(AccessQuery,
        function(err, row) {
            if(!err) {
                var locs = formatLatLng(row.latitude, row.longitude);
                loci = locationLookup[locs];
                if(!loci) {
                    loci = locationId++;
                    locationLookup[locs] = loci;
                    locationCache.push(locs);
                }
                ret.push([
                    parseInt(row.bitstream_id),
                    new Date(row.ts).toISOString().slice(0,16),
                    row.country_code,
                    loci
                    ]);
            }
        }, function(err, nrows) {
            callback(err, {access: ret, location: locationCache});
        });

}

function processCountryCodeTable(db, callback) {
    var countryTable = countriesByCCA2();
    var table = {};

    db.each(CountryCodeQuery, function(err, row) {
        if(!err) {
            var countryInfo = countryTable[row.country_code];
            if(countryInfo) {
                table[row.country_code] = [countryInfo.name, countryInfo.subregion, countryInfo.region];
            }
            else if (row.countryCode == 'EU') {
                table[row.country_code] = EUCountryInfo;
            }
            else {
                table[row.country_code] = [row.country_name, 'unknown', 'unknown'];
            }
        }
    },
    function(err, nrows) {
        callback(err, table);
    });
}

function countriesByCCA2() {
    var c = countries;
    var indexed = {};

    _.each(countries, function(x) {
        indexed[x.cca2] = x;
    });
    return indexed;
}

function formatLatLng(lat, lng) {
    return lat.toFixed(6) + ',' + lng.toFixed(6);
}

