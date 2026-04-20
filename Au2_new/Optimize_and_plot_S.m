% Extract parameter and plot

clear all;

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Initial values: Model parameter to be optimized

Vtho = 2.1006e+01;
delta = 8.2833e-02;
n = 1.1275e+02;
l = 1.0082e+00;
lam = 2.5865e+04;
Vgcrit = 6.6733e+01;
Jth = 6.2900e-05;
Rso = 1.9632e+06;
Vtun = 1;
V0 = 5;
Rmax = 1e8;
Idleak=5.4e-10;



%vscal = 1/(1-Vsc/Vmax) the drain current ID at VDS=Vmax 
%remains constant and only the ?linear? portion of the 
%output curve is affected.



W=0.1;           % Transistor width [cm]
typ=1;            % type of transistor. nFET type=1; pFET type=-1

kB=8.617e-5;        % Boltzmann constant [eV/K]
Tjun=293;           % Junction temperature [K].
phit = kB*Tjun;   



% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% The transfer curve has been shifted

shift = 0; %the shift used the the data to keep Vgs negative, write it as 
            % -"the shifted value"


% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Electrical characteristics

% Transfer 1
file1 = 'Au2_transfer0-60VF.csv';
Vds_1=50;
Vds1 = abs(Vds_1);
% Transfer 2
file2 = 'Au2_transfer0-60VB.csv';
Vds_2=50;
Vds2 = abs(Vds_2);

% Output 1
file3 = 'Au2_output60V.csv';
Vgs_1=47-shift;
Vgs1 = abs(Vgs_1);
% Output 2
file4 = 'Au2_output45V.csv';
Vgs_2=40-shift;
Vgs2 = abs(Vgs_2);
% Output 1
file5 = 'Au2_output30V.csv';
Vgs_3=33-shift;
Vgs3 = abs(Vgs_3);


% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

err = 1;
i = 0;
resnorm1min = 1;
resnorm2min = 1;

coeff = [Vtho, delta, n, l, lam, Vgcrit, Jth, Rso, Vtun, V0, Rmax];
global gp
gp = [Idleak, phit, W, Vds1, Vds2, Vgs1, Vgs2, Vgs3, typ];
[coeff_opt, resnorm1] = optimize_all_S(coeff, file1, file2, file3, file4, file5, @allcurvesS);

Vtho = coeff_opt(1);        
delta = coeff_opt(2);       
n = coeff_opt(3);            
l = coeff_opt(4);              
lam = coeff_opt(5);          
Vgcrit = coeff_opt(6);        
Jth=coeff_opt(7);
Rso = coeff_opt(8);
Vtun = coeff_opt(9);
V0 = coeff_opt(10);
Rmax = coeff_opt(11);


fprintf('Vtho = %.4e;\n', Vtho);
fprintf('delta = %.4e;\n', delta);
fprintf('n = %.4e;\n', n);
fprintf('l = %.4e;\n', l);
fprintf('lam = %.4e;\n', lam);
fprintf('Vgcrit = %.4e;\n', Vgcrit);
fprintf('Jth = %.4e;\n', Jth);
fprintf('Rso = %.4e;\n', Rso);
fprintf('Vtun = %.4e;\n', Vtun);
fprintf('V0 = %.4e;\n', V0);
fprintf('Rmax = %.4e;\n', Rmax);
fprintf('Real Vtho = %.4e;\n', shift+typ*Vtho);
%zValuesx=[Vtho,delta,n,l,lam,Vgcrit,Jth,Rso,Idleak,Rmax,Vtun];


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Now plot transfer
Vdv = [Vds_1 , Vds_2];  
mMVS=csvread(file1);
mMVSa = mMVS(:,2);
mMVSaV = mMVS(:,1);
mMVS=csvread(file2);
mMVSb = mMVS(:,2);
mMVSbV = mMVS(:,1);

% Object type: Line
set(0,'DefaultLineLineWidth',2);
set(0,'DefaultLineMarkerSize',8);

% Object type: Axes
set(0,'DefaultAxesFontName','Arial');
set(0,'DefaultAxesFontSize',10);
set(0,'DefaultAxesLineWidth',1.5);
set(0,'DefaultAxesTickLength',[0.02 0.02]);
set(0,'DefaultAxesUnits','normalized');
set(0,'DefaultAxesOuterPosition', [0 0 1 1]);
set(0,'DefaultAxesPosition',[0.15 0.15 0.7 0.7]);

% Object type: Text
set(0,'DefaultTextFontName','Arial');
set(0,'DefaultTextFontSize',16);
set(0,'DefaultTextInterpreter','remove')

% First five codes [0 0 1], [0 0.5 0], [1 0 0], [0 0.75 0.75], [0.75 0 0.75]
figure;
semilogy(mMVSaV+shift, mMVSa,'o','Color',[0 0 1]);
hold on;

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
for i=1:2
    
    % Model file
    % Direction of current flow:
    % dir=+1 when "x" terminal is the source
    % dir=-1 when "y" terminal is the source
    %CHANGED  Vg=0:-1:-30-shift;
    Vg=0:0.1:50-shift;
    Vd=Vdv(i);
    Vs=0;
    dir=typ*sign(Vd-Vs);
    
    Vds=abs(Vd-Vs);
    Vgs=max(typ*(Vg-Vs),typ*(Vg-Vd));
    
    
    %Drain impact
    Vtp=Vtho+Vds.*delta;
    
    % Total charge (normalized)
    nphit=n*phit;
    theta=(Vgs-Vtp)./(nphit);
    qtot = log(1+exp(theta));
    
    % Fsat calculation - Long channel device
    Vgt = nphit*qtot;
    Vgn = 2*Vgt./(1+sqrt(2*Vgt./Vgcrit));
    x = Vds./Vgn;
    eta = 1-tanh(x);
    y = Vgn./phit;
    ll = (2*lam./(y.*y.*(1-eta.*eta))).*(exp(y.*(eta-1)).*(1-y.*eta)-(1-y));
    if Vds(1) == 0 ll(1) = lam; end;
    tau = 1./(1+ll);
    at = tau./(2-tau); % 1/(1+2*ll)
    Fsat = at.*(1 - exp(-Vds./phit))./(1 + at.*exp(-Vds./phit));
    Fsat(isnan(Fsat))=0;
    
    % Current calculation
    Jfree = Jth.*qtot.^l;
    
    % Final
    Idx = Idleak + W.*Jfree.*Fsat;
    
    
    % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Vds -> Vdsi
    
    Idxx=Idleak;
    Rs = Rso + 0.5.*(Rmax-Rso).*(1-tanh((Vds-V0)./Vtun));
    Rd = Rso;
    dvg=Idx.*Rs;
    dvd=Idx.*Rd;
    count=1;
    
    while max(abs((Idx-Idxx)./Idx))>1e-10
        count=count+1;
        if count>500, break, end
        
        Idxx=Idx;
        dvg=0.2*Idx.*Rs+0.8*dvg;
        dvd=0.2*Idx.*Rd+0.8*dvd;
        %dvg=(Idx.*Rs+dvg)/2;
        %dvd=(Idx.*Rd+dvd)/2; CHANGED
        dvds=dvg+dvd;
        
        %Vdsi=max(Vds-dvds,0);
        %Vgsi=max(Vgs-dvg,0);
        %Vdsi=Vds-dvds;
        %Vgsi=Vgs-dvg; CHANGED
        if typ==-1
            Vdsi=Vds-dvds;     %p-type solution
            Vgsi=Vgs-dvg;
        else
            Vdsi=max(Vds-dvds,0);    %n-type solution
            Vgsi=max(Vgs-dvg,0);
        end
        %Drain impact
        Vtp=Vtho+Vdsi.*delta;
        
        % Total charge (normalized)
        nphit=n*phit;
        theta=(Vgsi-Vtp)./(nphit);
        qtot = log(1+exp(theta));
        
        % Fsat calculation - Long channel device
        Vgt = nphit*qtot;
        Vgn = 2*Vgt./(1+sqrt(2*Vgt./Vgcrit));
        x = Vdsi./Vgn;
        eta = 1-tanh(x);
        y = Vgn./phit;
        ll = (2*lam./(y.*y.*(1-eta.*eta))).*(exp(y.*(eta-1)).*(1-y.*eta)-(1-y));
        if Vdsi(1) == 0 ll(1) = lam; end;
        tau = 1./(1+ll);
        at = tau./(2-tau); % 1/(1+2*ll)
        Fsat = at.*(1 - exp(-Vdsi./phit))./(1 + at.*exp(-Vdsi./phit));
        Fsat(isnan(Fsat))=0;
        
        % Current calculation
        Jfree = Jth.*qtot.^l;
        
        % Final
        Idx = Idleak + W.*Jfree.*Fsat;
        
    end
    
    % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    % Wrapping up
    Id=typ*dir.*Idx;
    Id=Id';
    
    semilogy(Vg+shift,Id,'-','LineWidth',5,'Color',[0 0 0])
    hold on;
    
end

semilogy(mMVSbV+shift, mMVSb,'o','Color',[0 0 1]);
hold off;

% xlabel('VGS / V', 'fontsize', 16);
% ylabel('|ID| / A', 'fontsize', 16);


text(-28+shift,1e-6,'VDS=-3V','FontSize',15);
xlabel('$V_{\rm GS}$ / V','Interpreter','Latex','FontSize',15);
ylabel('$|I_{\rm D}|$ / A','Interpreter','Latex','FontSize',15);

%Ploting settings%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

set(gca, 'YScale', 'log'); %comente essa linha para plot linear
axis([0 50 1e-11 0.5e-4]); %ajuste estes valores para cada amostra
set(gca,'YTick', [0 1e-11 1e-10 1e-9 1e-8 1e-7 1e-6 1e-5]);
set(gca,'XTick',[-40 -30 -20 -10 0 10 20 30 40 50 60]);
leg=legend('Measurement','Model OVSED','Location','NorthWest');
set(leg,'Box','off');
set(leg,'FontSize',15);

print('FigTransfer', '-depsc'); %Imagem em eps colorido -depsc

% figure;
% loglog(mMVSbV, mMVSb, 'o','Color',[0 0 1]);
% hold on;
% loglog(Vg,Id);
% hold off;


%Plot output 1 now%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Vgv = [Vgs_1, Vgs_2, Vgs_3];
mMVS=csvread(file5);
mMVSa = mMVS(:,2);
mMVSaVd = mMVS(:,1)-0.75;
mMVS=csvread(file4);
mMVSb = mMVS(:,2);
mMVSbVd = mMVS(:,1)-0.75; 
mMVS=csvread(file3);
mMVSc = mMVS(:,2);
mMVScVd = mMVS(:,1)-0.75;

figure;
plot(mMVSaVd, mMVSa,'o','Color',[1 0 0]);
hold on;


for p=1:3
    % Model file
    % Direction of current flow:
    % dir=+1 when "x" terminal is the source
    % dir=-1 when "y" terminal is the source
    
    %Vd=0:-1:-30-shift; CHANGE
    Vd=0:0.2:50-shift;
    Vg=Vgv(p);
    Vs=0;
    dir=typ*sign(Vd-Vs);
    
    Vds=abs(Vd-Vs);
    Vgs=max(typ*(Vg-Vs),typ*(Vg-Vd));
    
    %Drain impact
    Vtp=Vtho+Vds.*delta;
    
    % Total charge (normalized)
    nphit=n*phit;
    theta=(Vgs-Vtp)./(nphit);
    qtot = log(1+exp(theta));
    
    % Fsat calculation - Long channel device
    Vgt = nphit*qtot;
    Vgn = 2*Vgt./(1+sqrt(2*Vgt./Vgcrit));
    x = Vds./Vgn;
    eta = 1-tanh(x);
    y = Vgn./phit;
    ll = (2*lam./(y.*y.*(1-eta.*eta))).*(exp(y.*(eta-1)).*(1-y.*eta)-(1-y));
    if Vds(1) == 0 ll(1) = lam; end;
    tau = 1./(1+ll);
    at = tau./(2-tau); % 1/(1+2*ll)
    Fsat = at.*(1 - exp(-Vds./phit))./(1 + at.*exp(-Vds./phit));
    Fsat(isnan(Fsat))=0;
    
    % Current calculation 
    Jfree = Jth.*qtot.^l;
    
    % Final
    Idx = Idleak + W.*Jfree.*Fsat;
      
    
    % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Vds -> Vdsi
    
    Idxx=Idleak;
    Rs = Rso + 0.5.*(Rmax-Rso).*(1-tanh((Vds-V0)./Vtun));
    Rd = Rso;
    dvg=Idx.*Rs;
    dvd=Idx.*Rd;
    count=1;
    
    while max(abs((Idx-Idxx)./Idx))>1e-10;
        count=count+1;
        if count>500, break, end
        
        Idxx=Idx;
        %dvg=(Idx.*Rs+dvg)/2;
        %dvd=(Idx.*Rd+dvd)/2; CHANGE
        dvg=0.2*Idx.*Rs+0.8*dvg;
        dvd=0.2*Idx.*Rd+0.8*dvd;
        dvds=dvg+dvd;
        
        %Vdsi=max(Vds-dvds,0);
        %Vgsi=max(Vgs-dvg,0);
        %Vdsi=Vds-dvds;
        %Vgsi=Vgs-dvg; CHANGE
        if typ==-1
            Vdsi=Vds-dvds;     %p-type solution
            Vgsi=Vgs-dvg;
        else
            Vdsi=max(Vds-dvds,0);    %n-type solution
            Vgsi=max(Vgs-dvg,0);
        end
        %Drain impact
        Vtp=Vtho+Vdsi.*delta;
        
        % Total charge (normalized)
        nphit=n*phit;
        theta=(Vgsi-Vtp)./(nphit);
        qtot = log(1+exp(theta));
        
        % Fsat calculation - Long channel device
        Vgt = nphit*qtot;
        Vgn = 2*Vgt./(1+sqrt(2*Vgt./Vgcrit));
        x = Vdsi./Vgn;
        eta = 1-tanh(x);
        y = Vgn./phit;
        ll = (2*lam./(y.*y.*(1-eta.*eta))).*(exp(y.*(eta-1)).*(1-y.*eta)-(1-y));
        if Vdsi(1) == 0 ll(1) = lam; end;
        tau = 1./(1+ll);
        at = tau./(2-tau); % 1/(1+2*ll)
        Fsat = at.*(1 - exp(-Vdsi./phit))./(1 + at.*exp(-Vdsi./phit));
        Fsat(isnan(Fsat))=0;
        
        % Current calculation
        Jfree = Jth.*qtot.^l;
        
        % Final
        Idx = Idleak + W.*Jfree.*Fsat;
        
    end
    
    % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    % Wrapping up
    Id=typ*dir.*Idx;
    Id=Id';
    
    plot(Vd,Id*1e6,'-','LineWidth',4,'Color',[0 0 0])
    hold on;
    
end

plot(mMVSbVd, mMVSb,'o','Color',[1 0 0]);
hold on;
plot(mMVScVd, mMVSc,'o','Color',[1 0 0]);
hold off;
% plot settings
text(-20,-750,'VGS=-0V','FontSize',15);
text(-20,-2500,'VGS=-10V','FontSize',15);
text(-13,-7000,'VGS=-30V','FontSize',15);
xlabel('$V_{\rm DS}$ / V','Interpreter','Latex','FontSize',15);
ylabel('$I_{\rm D}$ / uA','Interpreter','Latex','FontSize',15);
axis([0 50 0 1.2]); %ajuste estes valores para cada amostra
set(gca,'YTick', [0  0.10  0.20  0.30  0.40 0.50 0.6 0.7 0.8 0.9 1 1.1 1.2]);
set(gca,'XTick',[0 10 20 30 40 50 60]);
leg=legend('Measurement','Model OVSED','Location','NorthWest');
set(leg,'Box','off');
set(leg,'FontSize',15);

print('FigOutput', '-depsc'); %Imagem em eps colorido -depsc
