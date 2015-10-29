confirmed_creds="n"
echo
echo "Twitter Credentials"

while [ $confirmed_creds != "y" ]; do
	echo "-------------------"
    echo -n "consumer key: "
    read consumerkey
    echo -n "consumer secret: "
    read consumersecret
    echo -n "access token: "
    read accesstoken
    echo -n "access token secret: "
    read accesstokensecret
    echo
    cat <<EOF
TWITTER_CONSUMER_KEY=$consumerkey
TWITTER_CONSUMER_SECRET=$consumersecret
TWITTER_ACCESS_TOKEN=$accesstoken
TWITTER_ACCESS_TOKEN_SECRET=$accesstokensecret
EOF
	echo "----------------------"
    echo "is this correct? [y/n]"
    read confirmed_creds
done

echo
echo "sending credentials up to heroku..."
heroku config:add TWITTER_CONSUMER_KEY=$consumerkey \
    TWITTER_CONSUMER_SECRET=$consumersecret \
    TWITTER_ACCESS_TOKEN=$accesstoken \
    TWITTER_ACCESS_TOKEN_SECRET=$accesstokensecret

echo
echo "Spotify Credentials"

confirmed_creds="n"
while [ $confirmed_creds != "y" ]; do
	echo "-------------------"
	echo -n "username:"
	read spotifyusername
    echo -n "client id: "
    read clientid
    echo -n "client secret: "
    read clientsecret
    echo
    cat <<EOF
SPOTIPY_USERNAME=$spotifyusername
SPOTIPY_CLIENT_ID=$clientid
SPOTIPY_CLIENT_SECRET=$clientsecret
EOF
	echo "----------------------"
    echo "is this correct? [y/n]"
    read confirmed_creds
done

echo
echo "sending credentials up to heroku..."
heroku config:add SPOTIPY_USERNAME=$spotifyusername \
	SPOTIPY_CLIENT_ID=$clientid \
    SPOTIPY_CLIENT_SECRET=$clientsecret \

echo
echo "Google Credentials"

confirmed_creds="n"
while [ $confirmed_creds != "y" ]; do
	echo "------------------"
	echo -n "api key:"
	read apikey
	echo
    cat <<EOF
GOOGLE_API_KEY=$apikey
EOF
    echo "----------------------"
    echo "is this correct? [y/n]"
    read confirmed_creds
done

googleservice="youtube"
googleserviceversion="v3"

echo
echo "sending credentials up to heroku..."
heroku config:add GOOGLE_API_KEY=$apikey \
	GOOGLE_SERVICE="youtube" \
    GOOGLE_SERVICE_VERSION="v3" \

echo
echo "Reddit Credentials"

confirmed_creds="n"
while [ $confirmed_creds != "y" ]; do
	echo "------------------"
	echo -n "username:"
	read redditusername
	echo
    cat <<EOF
REDDIT_USERNAME=$apikey
EOF
    echo "----------------------"
    echo "is this correct? [y/n]"
    read confirmed_creds
done

echo
echo "sending credentials up to heroku..."
heroku config:add REDDIT_USERNAME=$redditusername

#create a script for setting up your local environment
cat <<EOF > setup_local_env.sh
export TWITTER_CONSUMER_KEY='$consumerkey'
export TWITTER_CONSUMER_SECRET=$consumersecret
export TWITTER_ACCESS_TOKEN=$accesstoken
export TWITTER_ACCESS_TOKEN_SECRET=$accesstokensecret

export SPOTIPY_USERNAME=$spotifyusername
export SPOTIPY_CLIENT_ID=$clientid
export SPOTIPY_CLIENT_SECRET=$clientsecret

export GOOGLE_API_KEY=$apikey
export GOOGLE_SERVICE=$googleservice
export GOOGLE_SERVICE_VERSION=$googleserviceversion

export REDDIT_USERNAME=$redditusername
EOF

#create a script for setting up your local environment
cat <<EOF > setup_heroku_env.sh
heroku config:add TWITTER_CONSUMER_KEY=$consumerkey \
    TWITTER_CONSUMER_SECRET=$consumersecret \
    TWITTER_ACCESS_TOKEN=$accesstoken \
    TWITTER_ACCESS_TOKEN_SECRET=$accesstokensecret

heroku config:add SPOTIPY_USERNAME=$spotifyusername \
	SPOTIPY_CLIENT_ID=$clientid \
    SPOTIPY_CLIENT_SECRET=$clientsecret \

heroku config:add GOOGLE_API_KEY=$apikey \
	GOOGLE_SERVICE="youtube" \
    GOOGLE_SERVICE_VERSION="v3" \

heroku config:add REDDIT_USERNAME=$redditusername
EOF

echo
echo "run \"source setup_local_env.sh\" to setup environment for local deployments"
echo "run \"source setup_heroku_env.sh\" to resend credentials to heroku"