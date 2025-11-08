Please note:

If your computer does not yet have Java 11 (or later) installed, then when you try to launch
Panoply, it may display a dialog indicating that you need to install Java 11.

Please note that you will also get this message if the Panoply.exe Java launcher cannot
determine where to find your Java 11+ installation. This could happen if you installed a
non-Oracle open source Java distribution that does not write Java location information to the
Windows registry.

Even if the Windows registry keys have not been written, the Panoply.exe launcher will also
check if the %JAVA_HOME% environment variable has been set and try to use that location.
However, if the Java located there is not Java 11 or later, then Panoply may crash without
displaying any message.

Because of licensing issues, many organizations that use Java have opted to use one of the
several alternative open source Java distributions such as Adoptium's Temurin, Amazon Corretto,
Azul Zulu, etc. Panoply users have reported good results using Temurin, available at

    https://adoptium.net/

The Temurin installer on Windows will display a panel labeled "Custom Setup". In this panel, you
MUST specifically enable the "Set JAVA_HOME variable" and "JavaSoft registry keys" options. By
default they are not enabled.

If you have any questions and/or are installing Java on your office computer, we suggest that
you communicate with your organization's IT staff for any recommendations that they may have
about installing Java and any possible licensing concerns.
